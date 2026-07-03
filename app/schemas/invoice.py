from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import uuid

class InvoiceItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int
    rate: float
    discount_pct: float = 0.00

class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    items: List[InvoiceItemCreate]
    transport_charges: float = 0.00
    terms: Optional[str] = None
    invoice_date: Optional[date] = None

class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    quantity: int
    rate: float
    discount_pct: float
    subtotal: float
    gst_rate: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total_amount: float

    class Config:
        from_attributes = True

class InvoiceOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID
    invoice_date: date
    subtotal: float
    cgst_total: float
    sgst_total: float
    igst_total: float
    transport_charges: float
    grand_total: float
    terms: Optional[str] = None
    status: str
    items: List[InvoiceItemOut]
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
