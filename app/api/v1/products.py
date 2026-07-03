from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api import deps
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductOut, ProductCreate, ProductUpdate, StockAdjustment

router = APIRouter()

@router.get("/", response_model=List[ProductOut])
async def list_products(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    low_stock: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Product).where(Product.deleted_at == None)
    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.category.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.where(Product.category == category)
    if low_stock:
        query = query.where(Product.stock < 50)
    query = query.order_by(Product.name.asc())
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product.category).where(Product.deleted_at == None).distinct())
    categories = result.scalars().all()
    return [c for c in categories if c is not None]

@router.get("/{id}", response_model=ProductOut)
async def get_product(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == id, Product.deleted_at == None))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Check SKU uniqueness (only active products)
    existing = await db.execute(select(Product).where(Product.sku == product_in.sku, Product.deleted_at == None))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    product = Product(**product_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.put("/{id}", response_model=ProductOut)
async def update_product(
    id: uuid.UUID,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == id, Product.deleted_at == None))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == id, Product.deleted_at == None))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Soft delete
    product.deleted_at = func.now()
    db.add(product)
    await db.commit()

@router.post("/{id}/adjust-stock", response_model=ProductOut)
async def adjust_stock(
    id: uuid.UUID,
    adjustment: StockAdjustment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == id, Product.deleted_at == None))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if adjustment.adjustment_type == "inbound":
        product.stock += adjustment.quantity
    elif adjustment.adjustment_type == "outbound":
        if product.stock < adjustment.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {product.stock}")
        product.stock -= adjustment.quantity
    else:
        raise HTTPException(status_code=400, detail="Invalid adjustment type. Use 'inbound' or 'outbound'")
    
    await db.commit()
    await db.refresh(product)
    return product
