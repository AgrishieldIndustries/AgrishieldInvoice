from sqlalchemy import Column, String, Integer
from app.core.database import Base

class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, default=1)
    company_name = Column(String(255), nullable=False, default="Agrishield Industries Pvt Ltd")
    gstin = Column(String(15), nullable=False, default="27AAACA9999A1Z2") # Pune Maharashtra default
    address = Column(String(500), nullable=False, default="Gat No. 120, Chakan-Talegaon Road, Chakan, Pune, Maharashtra, 410501, India")
    phone = Column(String(15), nullable=False, default="+91 2135 249000")
    email = Column(String(255), nullable=False, default="info@agrishield.in")
    bank_name = Column(String(255), nullable=False, default="State Bank of India")
    bank_ifsc = Column(String(20), nullable=False, default="SBIN0001234")
    bank_account_no = Column(String(50), nullable=False, default="330011223344")
    terms_and_conditions = Column(String(2000), nullable=False, default="1. Goods once sold will not be taken back.\n2. Interest @ 18% p.a. will be charged if payment is not made within 30 days.\n3. Subject to Pune jurisdiction.")
    logo_url = Column(String(500), nullable=True)
