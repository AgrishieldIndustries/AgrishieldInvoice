from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func
from typing import List, Optional
import uuid
from datetime import date

from app.core.database import get_db
from app.api import deps
from app.models.payment import Payment, PaymentMode, PaymentStatus
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User
from app.schemas.payment import PaymentOut, PaymentCreate, PaymentUpdate

router = APIRouter()

@router.get("/", response_model=List[PaymentOut])
async def list_payments(
    customer_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Payment).where(Payment.deleted_at == None)
    if customer_id:
        query = query.where(Payment.customer_id == customer_id)
    query = query.order_by(Payment.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Validate customer
    cust_result = await db.execute(select(Customer).where(Customer.id == payment_in.customer_id, Customer.deleted_at == None))
    customer = cust_result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Validate invoice if provided
    if payment_in.invoice_id:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == payment_in.invoice_id, Invoice.deleted_at == None))
        invoice = inv_result.scalars().first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

    # Map payment mode
    try:
        mode = PaymentMode(payment_in.payment_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment mode: {payment_in.payment_mode}")
    
    # Map status
    try:
        pay_status = PaymentStatus(payment_in.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment status: {payment_in.status}")

    payment = Payment(
        customer_id=payment_in.customer_id,
        invoice_id=payment_in.invoice_id,
        payment_date=payment_in.payment_date or date.today(),
        amount=payment_in.amount,
        payment_mode=mode,
        reference_number=payment_in.reference_number,
        status=pay_status,
        notes=payment_in.notes,
        created_by=current_user.id
    )
    db.add(payment)

    # If payment is Cleared, reduce customer outstanding balance
    if pay_status == PaymentStatus.CLEARED:
        customer.outstanding_balance = max(0.0, float(customer.outstanding_balance) - payment_in.amount)
        
        # Update invoice status if linked
        if payment_in.invoice_id:
            inv_result = await db.execute(select(Invoice).where(Invoice.id == payment_in.invoice_id, Invoice.deleted_at == None))
            invoice = inv_result.scalars().first()
            if invoice:
                # Check total payments for this invoice
                all_payments_result = await db.execute(
                    select(Payment).where(
                        Payment.invoice_id == payment_in.invoice_id,
                        Payment.status == PaymentStatus.CLEARED,
                        Payment.deleted_at == None
                    )
                )
                existing_payments = all_payments_result.scalars().all()
                total_paid = sum(float(p.amount) for p in existing_payments) + payment_in.amount
                
                if total_paid >= float(invoice.grand_total):
                    invoice.status = InvoiceStatus.PAID
                elif total_paid > 0:
                    invoice.status = InvoiceStatus.PARTIALLY_PAID

    await db.commit()
    await db.refresh(payment)
    return payment

@router.put("/{id}", response_model=PaymentOut)
async def update_payment(
    id: uuid.UUID,
    payment_in: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Payment).where(Payment.id == id, Payment.deleted_at == None))
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    update_data = payment_in.model_dump(exclude_unset=True)
    if "status" in update_data:
        try:
            update_data["status"] = PaymentStatus(update_data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    for field, value in update_data.items():
        setattr(payment, field, value)
    
    await db.commit()
    await db.refresh(payment)
    return payment

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Payment).where(Payment.id == id, Payment.deleted_at == None))
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # If was cleared, restore outstanding balance
    if payment.status == PaymentStatus.CLEARED:
        cust_result = await db.execute(select(Customer).where(Customer.id == payment.customer_id, Customer.deleted_at == None))
        customer = cust_result.scalars().first()
        if customer:
            customer.outstanding_balance += payment.amount
    
    # Soft delete
    payment.deleted_at = func.now()
    db.add(payment)
    await db.commit()
