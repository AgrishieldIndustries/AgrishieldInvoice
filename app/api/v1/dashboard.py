from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import date, timedelta

from app.core.database import get_db
from app.api import deps
from app.models.invoice import Invoice
from app.models.customer import Customer
from app.models.product import Product
from app.models.payment import Payment, PaymentStatus
from app.models.user import User

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    today = date.today()
    month_start = today.replace(day=1)
    
    # Today's sales
    today_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total), 0))
        .where(Invoice.invoice_date == today)
    )
    today_sales = float(today_result.scalar())
    
    # Monthly sales
    monthly_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total), 0))
        .where(Invoice.invoice_date >= month_start)
    )
    monthly_sales = float(monthly_result.scalar())
    
    # Total outstanding
    outstanding_result = await db.execute(
        select(func.coalesce(func.sum(Customer.outstanding_balance), 0))
    )
    total_outstanding = float(outstanding_result.scalar())
    
    # Overdue invoices count (Unpaid/Partially Paid older than 30 days)
    overdue_result = await db.execute(
        select(func.count(Invoice.id))
        .where(
            Invoice.status.in_(['Unpaid', 'Partially Paid']),
            Invoice.invoice_date < today - timedelta(days=30)
        )
    )
    overdue_count = int(overdue_result.scalar())
    
    # Low stock count
    low_stock_result = await db.execute(
        select(func.count(Product.id)).where(Product.stock < 50)
    )
    low_stock_count = int(low_stock_result.scalar())
    
    # Total customers
    customer_count_result = await db.execute(select(func.count(Customer.id)))
    total_customers = int(customer_count_result.scalar())
    
    # Total products
    product_count_result = await db.execute(select(func.count(Product.id)))
    total_products = int(product_count_result.scalar())
    
    # Recent invoices (last 5)
    recent_inv_result = await db.execute(
        select(Invoice).order_by(Invoice.created_at.desc()).limit(5)
    )
    recent_invoices = recent_inv_result.scalars().all()
    
    # Get customer names for recent invoices
    recent_inv_list = []
    for inv in recent_invoices:
        cust_result = await db.execute(select(Customer).where(Customer.id == inv.customer_id))
        cust = cust_result.scalars().first()
        recent_inv_list.append({
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "customer_name": cust.name if cust else "Unknown",
            "shop_name": cust.shop_name if cust else "Unknown",
            "invoice_date": str(inv.invoice_date),
            "grand_total": float(inv.grand_total),
            "status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
        })
    
    return {
        "today_sales": today_sales,
        "monthly_sales": monthly_sales,
        "total_outstanding": total_outstanding,
        "overdue_invoices": overdue_count,
        "low_stock_items": low_stock_count,
        "total_customers": total_customers,
        "total_products": total_products,
        "recent_invoices": recent_inv_list,
    }
