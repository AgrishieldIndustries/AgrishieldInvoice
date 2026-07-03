from pydantic import BaseModel
from typing import Optional

class CompanySettingsBase(BaseModel):
    company_name: str
    gstin: str
    address: str
    phone: str
    email: str
    bank_name: str
    bank_ifsc: str
    bank_account_no: str
    terms_and_conditions: str
    logo_url: Optional[str] = None

class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    bank_name: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_no: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    logo_url: Optional[str] = None

class CompanySettingsOut(CompanySettingsBase):
    id: int

    class Config:
        from_attributes = True
