from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.product import Product
from app.models.inventory import InventoryHistory
from app.schemas.inventory import InventoryHistoryOut

router = APIRouter()

@router.post("/{product_id}/adjust-stock")
async def adjust_stock(
    product_id: uuid.UUID,
    adjustment: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Adjust product stock level (inbound or outbound).
    Body: { "adjustment_type": "inbound"|"outbound", "quantity": int, "reason": str }
    """
    adjustment_type = adjustment.get("adjustment_type")
    quantity = adjustment.get("quantity")
    reason = adjustment.get("reason", "")

    if adjustment_type not in ("inbound", "outbound"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="adjustment_type must be 'inbound' or 'outbound'"
        )
    if not isinstance(quantity, int) or quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quantity must be a positive integer"
        )

    # Get product
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at == None))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Apply adjustment
    if adjustment_type == "outbound":
        if product.stock < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.stock}, Requested: {quantity}"
            )
        product.stock -= quantity
        log_quantity = -quantity
    else:
        product.stock += quantity
        log_quantity = quantity

    # Create inventory history log
    history = InventoryHistory(
        product_id=product_id,
        quantity=log_quantity,
        adjustment_type=adjustment_type,
        reason=reason,
        created_by=current_user.id,
    )
    db.add(history)
    await db.flush()

    return {
        "message": f"Stock {'increased' if adjustment_type == 'inbound' else 'decreased'} by {quantity}",
        "product_id": str(product_id),
        "new_stock": product.stock,
    }


@router.get("/history", response_model=List[InventoryHistoryOut])
async def get_inventory_history(
    product_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve inventory movement history, optionally filtered by product.
    """
    query = select(InventoryHistory)
    if product_id:
        query = query.where(InventoryHistory.product_id == product_id)
    query = query.order_by(InventoryHistory.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
