from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid

class PaymentCreate(BaseModel):
    customer_id: uuid.UUID
    invoice_id: Optional[uuid.UUID] = None
    payment_date: Optional[date] = None
    amount: float
    payment_mode: str  # Cash, Cheque, NEFT, RTGS, UPI
    reference_number: Optional[str] = None
    status: str = "Cleared"  # Pending, Cleared, Bounced
    notes: Optional[str] = None

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None

class PaymentOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    invoice_id: Optional[uuid.UUID] = None
    payment_date: date
    amount: float
    payment_mode: str
    reference_number: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
