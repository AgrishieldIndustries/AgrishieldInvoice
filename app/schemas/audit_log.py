from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
