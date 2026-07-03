from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api import deps
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.customer import CustomerOut, CustomerCreate, CustomerUpdate

router = APIRouter()

@router.get("/", response_model=List[CustomerOut])
async def list_customers(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Customer).where(Customer.deleted_at == None)
    if search:
        query = query.where(
            or_(
                Customer.shop_name.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Customer.gstin.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(Customer.shop_name.asc())
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{id}", response_model=CustomerOut)
async def get_customer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.id == id, Customer.deleted_at == None))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    customer = Customer(**customer_in.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer

@router.put("/{id}", response_model=CustomerOut)
async def update_customer(
    id: uuid.UUID,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.id == id, Customer.deleted_at == None))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.id == id, Customer.deleted_at == None))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Check if customer has invoices
    inv_result = await db.execute(select(Invoice).where(Invoice.customer_id == id, Invoice.deleted_at == None))
    if inv_result.scalars().first():
        raise HTTPException(status_code=400, detail="Cannot delete customer with existing invoices.")
    
    # Soft delete
    customer.deleted_at = func.now()
    db.add(customer)
    await db.commit()

@router.get("/{id}/ledger")
async def get_customer_ledger(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Get customer
    result = await db.execute(select(Customer).where(Customer.id == id, Customer.deleted_at == None))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get customer invoices
    inv_result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.customer_id == id, Invoice.deleted_at == None)
        .order_by(Invoice.created_at.desc())
    )
    invoices = inv_result.scalars().all()
    
    # Get customer payments
    from app.models.payment import Payment
    pay_result = await db.execute(
        select(Payment)
        .where(Payment.customer_id == id, Payment.deleted_at == None)
        .order_by(Payment.payment_date.desc())
    )
    payments = pay_result.scalars().all()
    
    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "shop_name": customer.shop_name,
            "phone": customer.phone,
            "gstin": customer.gstin,
            "billing_address": customer.billing_address,
            "shipping_address": customer.shipping_address,
            "credit_limit": float(customer.credit_limit),
            "outstanding_balance": float(customer.outstanding_balance),
        },
        "invoices": [{
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "invoice_date": str(inv.invoice_date),
            "grand_total": float(inv.grand_total),
            "status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
        } for inv in invoices],
        "payments": [{
            "id": str(p.id),
            "payment_date": str(p.payment_date),
            "amount": float(p.amount),
            "payment_mode": p.payment_mode.value if hasattr(p.payment_mode, 'value') else str(p.payment_mode),
            "reference_number": p.reference_number,
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
        } for p in payments]
    }
