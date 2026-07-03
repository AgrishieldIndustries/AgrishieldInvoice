import asyncio
from datetime import date
from sqlalchemy.future import select
from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
# Import ALL models so Base.metadata knows about every table
from app.models import (
    User, UserRole, Customer, Product, CompanySettings,
    Invoice, InvoiceItem, Payment, InventoryHistory, AuditLog
)

async def seed_data():
    print("Dropping and recreating all database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("Seeding database values...")
    async with SessionLocal() as session:
        # 1. Seed Admin User
        result = await session.execute(select(User).where(User.email == "admin@agrishield.in"))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                email="admin@agrishield.in",
                hashed_password=get_password_hash("admin123"),
                full_name="Agrishield Admin Team",
                role=UserRole.ADMIN,
                is_active=True
            )
            session.add(admin)
            print("Seeded Admin: admin@agrishield.in / admin123")
        else:
            print("Admin user already exists.")

        # 2. Seed Company Settings
        settings_result = await session.execute(select(CompanySettings).where(CompanySettings.id == 1))
        settings = settings_result.scalars().first()
        if not settings:
            settings = CompanySettings()
            session.add(settings)
            print("Seeded default Company Settings.")

        # 3. Seed Customers
        customers_check = await session.execute(select(Customer))
        if not customers_check.scalars().first():
            c1 = Customer(
                name="Sanjay Patil",
                shop_name="Sai Agro Agencies",
                phone="9822114400",
                gstin="27AAAPS1234A1Z0", # starts with 27 -> Maharashtra (Intra-state CGST+SGST)
                billing_address="Ganesh Peth, Chakan, Pune, MH - 410501",
                shipping_address="Ganesh Peth, Chakan, Pune, MH - 410501",
                credit_limit=100000.00,
                outstanding_balance=0.00
            )
            c2 = Customer(
                name="Ramesh Shinde",
                shop_name="Balaji Fertilizers",
                phone="9860405060",
                gstin="27AAAPB5678A1Z5", # starts with 27 -> Maharashtra (Intra-state CGST+SGST)
                billing_address="Market Yard, Nashik, MH - 422001",
                shipping_address="Market Yard, Nashik, MH - 422001",
                credit_limit=150000.00,
                outstanding_balance=0.00
            )
            c3 = Customer(
                name="Malleshappa Biradar",
                shop_name="Kisan Krishi Seva Kendra",
                phone="9980556677",
                gstin="29AAAPK1212B1Z1", # starts with 29 -> Karnataka (Inter-state IGST)
                billing_address="Main Road, Bidar, KA - 585401",
                shipping_address="Main Road, Bidar, KA - 585401",
                credit_limit=80000.00,
                outstanding_balance=0.00
            )
            session.add_all([c1, c2, c3])
            print("Seeded 3 Customers.")
        else:
            print("Customers already seeded.")

        # 4. Seed Products
        products_check = await session.execute(select(Product))
        if not products_check.scalars().first():
            p1 = Product(
                name="Water Soluble Fertilizer NPK 19:19:19",
                sku="AGR-WSF-191919-25K",
                category="WSF",
                npk_ratio="19:19:19",
                hsn_code="31052000",
                gst_rate=18.00,
                mrp=1200.00,
                dealer_price=950.00,
                distributor_price=900.00,
                batch_number="B-1919-26A",
                mfg_date=date(2026, 6, 1),
                expiry_date=date(2029, 6, 1),
                stock=500
            )
            p2 = Product(
                name="Single Super Phosphate (SSP)",
                sku="AGR-FER-SSP-50K",
                category="Fertilizers",
                npk_ratio="0:16:0",
                hsn_code="31031100",
                gst_rate=12.00,
                mrp=650.00,
                dealer_price=480.00,
                distributor_price=450.00,
                batch_number="B-SSP-26D",
                mfg_date=date(2026, 5, 15),
                expiry_date=date(2029, 5, 15),
                stock=1200
            )
            p3 = Product(
                name="Plant Growth Regulator (PGR) Nitrobenzene 20%",
                sku="AGR-PGR-NB20-1L",
                category="PGR",
                npk_ratio=None,
                hsn_code="38089340",
                gst_rate=18.00,
                mrp=450.00,
                dealer_price=350.00,
                distributor_price=320.00,
                batch_number="B-NTR-26G",
                mfg_date=date(2026, 6, 10),
                expiry_date=date(2028, 6, 10),
                stock=300
            )
            session.add_all([p1, p2, p3])
            print("Seeded 3 Products.")
        else:
            print("Products already seeded.")

        await session.commit()
        print("Database Seeding Finished Successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
