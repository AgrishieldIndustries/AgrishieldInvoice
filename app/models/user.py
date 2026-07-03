from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid
import enum

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    ACCOUNTANT = "Accountant"
    SALES_EXECUTIVE = "Sales Executive"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role", inherit_schema=True), nullable=False, default=UserRole.SALES_EXECUTIVE)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
