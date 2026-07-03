from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    npk_ratio = Column(String(20), nullable=True)
    hsn_code = Column(String(10), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False, default=18.00)
    mrp = Column(Numeric(10, 2), nullable=False)
    dealer_price = Column(Numeric(10, 2), nullable=False)
    distributor_price = Column(Numeric(10, 2), nullable=False)
    batch_number = Column(String(50), nullable=False)
    mfg_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
