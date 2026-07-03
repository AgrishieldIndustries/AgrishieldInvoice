from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List
import uuid
from datetime import date

from app.core.database import get_db
from app.api import deps
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.customer import Customer
from app.models.product import Product
from app.models.company_settings import CompanySettings
from app.models.user import User
from app.schemas.invoice import InvoiceOut, InvoiceCreate
from app.services.billing import calculate_taxes_for_item, check_is_interstate
from app.services.pdf_generator import generate_invoice_pdf

router = APIRouter()

@router.get("/", response_model=List[InvoiceOut])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.deleted_at == None)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()

@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Fetch Customer (must be active)
    customer_result = await db.execute(select(Customer).where(Customer.id == invoice_in.customer_id, Customer.deleted_at == None))
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    is_interstate = check_is_interstate(customer)

    # Calculate sequential invoice number (include deleted for sequence safety)
    count_result = await db.execute(select(Invoice))
    invoice_count = len(count_result.scalars().all())
    invoice_number = f"AS/26-27/{invoice_count + 1:04d}"

    # Totals
    subtotal_total = 0.0
    cgst_total = 0.0
    sgst_total = 0.0
    igst_total = 0.0
    items_to_create = []

    for item_in in invoice_in.items:
        # Fetch Product (must be active)
        prod_result = await db.execute(select(Product).where(Product.id == item_in.product_id, Product.deleted_at == None))
        product = prod_result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item_in.product_id} not found")
        
        # Verify Stock
        if product.stock < item_in.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {product.name}. Requested: {item_in.quantity}, Available: {product.stock}"
            )

        # Compute line tax & subtotal
        calc = calculate_taxes_for_item(
            quantity=item_in.quantity,
            rate=item_in.rate,
            discount_pct=item_in.discount_pct,
            gst_rate=float(product.gst_rate),
            is_interstate=is_interstate
        )

        # Update totals
        subtotal_total += calc["subtotal"]
        cgst_total += calc["cgst_amount"]
        sgst_total += calc["sgst_amount"]
        igst_total += calc["igst_amount"]

        # Create Invoice Item
        db_item = InvoiceItem(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            quantity=item_in.quantity,
            rate=item_in.rate,
            discount_pct=item_in.discount_pct,
            subtotal=calc["subtotal"],
            gst_rate=product.gst_rate,
            cgst_amount=calc["cgst_amount"],
            sgst_amount=calc["sgst_amount"],
            igst_amount=calc["igst_amount"],
            total_amount=calc["total_amount"]
        )
        items_to_create.append(db_item)

        # Deduct Product stock
        product.stock -= item_in.quantity

    # Grand total
    grand_total = subtotal_total + cgst_total + sgst_total + igst_total + float(invoice_in.transport_charges)

    # Create Invoice header
    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=customer.id,
        invoice_date=invoice_in.invoice_date or date.today(),
        subtotal=subtotal_total,
        cgst_total=cgst_total,
        sgst_total=sgst_total,
        igst_total=igst_total,
        transport_charges=invoice_in.transport_charges,
        grand_total=grand_total,
        terms=invoice_in.terms,
        status=InvoiceStatus.UNPAID,
        created_by=current_user.id
    )

    db.add(invoice)
    await db.flush()

    # Add items to invoice relation
    for item in items_to_create:
        item.invoice_id = invoice.id
        db.add(item)

    # Update Customer outstanding balance
    from decimal import Decimal
    customer.outstanding_balance = Decimal(str(customer.outstanding_balance)) + Decimal(str(invoice.grand_total))

    await db.commit()
    await db.refresh(invoice)
    return invoice

@router.get("/{id}", response_model=InvoiceOut)
async def get_invoice(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.id == id, Invoice.deleted_at == None)
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.post("/{id}/cancel", response_model=InvoiceOut)
async def cancel_invoice(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Cancel an invoice: marks status as Cancelled, reverts product stocks, and subtracts grand total from customer outstanding balance.
    """
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.id == id, Invoice.deleted_at == None)
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Invoice is already cancelled")

    # Fetch Customer
    customer_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
    customer = customer_res.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Revert product stocks
    for item in invoice.items:
        prod_res = await db.execute(select(Product).where(Product.id == item.product_id))
        product = prod_res.scalars().first()
        if product:
            product.stock += item.quantity

    # Revert customer outstanding balance
    from decimal import Decimal
    customer.outstanding_balance = max(Decimal("0.00"), Decimal(str(customer.outstanding_balance)) - Decimal(str(invoice.grand_total)))

    # Mark invoice as Cancelled
    invoice.status = InvoiceStatus.CANCELLED
    await db.commit()
    await db.refresh(invoice)
    return invoice

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Soft delete an invoice. If it was active, it must be cancelled first to ensure stock & balances are reconciled.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == id, Invoice.deleted_at == None))
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Active invoices must be Cancelled before they can be deleted.")

    invoice.deleted_at = func.now()
    await db.commit()

@router.get("/{id}/pdf")
async def download_pdf(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Fetch Invoice
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(Invoice.id == id, Invoice.deleted_at == None)
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Fetch Customer
    customer_res = await db.execute(select(Customer).where(Customer.id == invoice.customer_id))
    customer = customer_res.scalars().first()

    # Fetch Company Settings
    company_res = await db.execute(select(CompanySettings).where(CompanySettings.id == 1))
    company = company_res.scalars().first()

    # Generate PDF bytes
    pdf_buffer = generate_invoice_pdf(invoice, customer, company)

    # Return as stream
    filename = f"invoice_{invoice.invoice_number.replace('/', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
