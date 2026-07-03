from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class InventoryHistoryOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    adjustment_type: str
    reason: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
