from sqlalchemy import Column, String, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    shop_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(15), nullable=False, index=True)
    gstin = Column(String(15), nullable=True)
    billing_address = Column(String(500), nullable=False)
    shipping_address = Column(String(500), nullable=False)
    credit_limit = Column(Numeric(12, 2), nullable=False, default=0.00)
    outstanding_balance = Column(Numeric(12, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
