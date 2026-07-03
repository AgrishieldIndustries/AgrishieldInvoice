from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class CustomerBase(BaseModel):
    name: str
    shop_name: str
    phone: str
    gstin: Optional[str] = None
    billing_address: str
    shipping_address: str
    credit_limit: float = 0.00

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    shop_name: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    credit_limit: Optional[float] = None

class CustomerOut(CustomerBase):
    id: uuid.UUID
    outstanding_balance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
