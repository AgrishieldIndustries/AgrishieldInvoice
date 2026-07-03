from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
import enum

class InvoiceStatus(str, enum.Enum):
    PAID = "Paid"
    UNPAID = "Unpaid"
    PARTIALLY_PAID = "Partially Paid"
    CANCELLED = "Cancelled"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False, server_default=func.current_date())
    subtotal = Column(Numeric(12, 2), nullable=False)
    cgst_total = Column(Numeric(12, 2), nullable=False, default=0.00)
    sgst_total = Column(Numeric(12, 2), nullable=False, default=0.00)
    igst_total = Column(Numeric(12, 2), nullable=False, default=0.00)
    transport_charges = Column(Numeric(10, 2), nullable=False, default=0.00)
    grand_total = Column(Numeric(12, 2), nullable=False)
    terms = Column(String(1000), nullable=True)
    status = Column(SQLEnum(InvoiceStatus, name="invoice_status", inherit_schema=True), nullable=False, default=InvoiceStatus.UNPAID)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    customer = relationship("Customer")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    rate = Column(Numeric(10, 2), nullable=False)
    discount_pct = Column(Numeric(5, 2), nullable=False, default=0.00)
    subtotal = Column(Numeric(12, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    cgst_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    sgst_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    igst_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Relations
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
