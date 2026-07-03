from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
import enum

class PaymentMode(str, enum.Enum):
    CASH = "Cash"
    CHEQUE = "Cheque"
    NEFT = "NEFT"
    RTGS = "RTGS"
    UPI = "UPI"

class PaymentStatus(str, enum.Enum):
    PENDING = "Pending"
    CLEARED = "Cleared"
    BOUNCED = "Bounced"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    payment_date = Column(Date, nullable=False, server_default=func.current_date())
    amount = Column(Numeric(12, 2), nullable=False)
    payment_mode = Column(SQLEnum(PaymentMode, name="payment_mode", inherit_schema=True), nullable=False)
    reference_number = Column(String(100), nullable=True)
    status = Column(SQLEnum(PaymentStatus, name="payment_status", inherit_schema=True), nullable=False, default=PaymentStatus.CLEARED)
    notes = Column(String(500), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relations
    customer = relationship("Customer")
    invoice = relationship("Invoice")
