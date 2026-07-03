from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid

class ProductBase(BaseModel):
    name: str
    sku: str
    category: str
    npk_ratio: Optional[str] = None
    hsn_code: str
    gst_rate: float
    mrp: float
    dealer_price: float
    distributor_price: float
    batch_number: str
    mfg_date: date
    expiry_date: date
    stock: int = 0

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    npk_ratio: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    mrp: Optional[float] = None
    dealer_price: Optional[float] = None
    distributor_price: Optional[float] = None
    batch_number: Optional[str] = None
    mfg_date: Optional[date] = None
    expiry_date: Optional[date] = None
    stock: Optional[int] = None

class StockAdjustment(BaseModel):
    adjustment_type: str  # "inbound" or "outbound"
    quantity: int
    reason: Optional[str] = None

class ProductOut(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
