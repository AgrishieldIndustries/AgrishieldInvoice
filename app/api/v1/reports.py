from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, extract, case
from typing import Optional
from datetime import date, timedelta
import uuid

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.product import Product
from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus
from decimal import Decimal

router = APIRouter()

@router.get("/sales")
async def get_sales_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Sales analytics report with breakdowns by product, category, and customer.
    Defaults to current month if no date range is specified.
    """
    today = date.today()
    if not start_date:
        start_date = today.replace(day=1)
    if not end_date:
        end_date = today

    # Base query: only non-cancelled invoices within the date range
    base_filter = [
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
        Invoice.status != InvoiceStatus.CANCELLED,
        Invoice.deleted_at == None,
    ]

    # 1. Summary totals
    summary_query = select(
        func.count(Invoice.id).label("total_invoices"),
        func.coalesce(func.sum(Invoice.grand_total), 0).label("total_revenue"),
        func.coalesce(func.sum(Invoice.cgst_total + Invoice.sgst_total + Invoice.igst_total), 0).label("total_tax"),
        func.coalesce(func.sum(Invoice.transport_charges), 0).label("total_transport"),
    ).where(*base_filter)
    summary_result = await db.execute(summary_query)
    summary = summary_result.first()

    # 2. Sales by product (top sellers)
    product_sales_query = select(
        InvoiceItem.product_name,
        InvoiceItem.sku,
        func.sum(InvoiceItem.quantity).label("total_qty"),
        func.sum(InvoiceItem.total_amount).label("total_amount"),
    ).join(
        Invoice, InvoiceItem.invoice_id == Invoice.id
    ).where(
        *base_filter
    ).group_by(
        InvoiceItem.product_name, InvoiceItem.sku
    ).order_by(
        func.sum(InvoiceItem.total_amount).desc()
    ).limit(20)
    product_result = await db.execute(product_sales_query)
    product_sales = product_result.all()

    # 3. Sales by customer
    customer_sales_query = select(
        Customer.id,
        Customer.shop_name,
        Customer.name,
        func.count(Invoice.id).label("invoice_count"),
        func.coalesce(func.sum(Invoice.grand_total), 0).label("total_amount"),
    ).join(
        Invoice, Customer.id == Invoice.customer_id
    ).where(
        *base_filter
    ).group_by(
        Customer.id, Customer.shop_name, Customer.name
    ).order_by(
        func.sum(Invoice.grand_total).desc()
    ).limit(20)
    customer_result = await db.execute(customer_sales_query)
    customer_sales = customer_result.all()

    # 4. Collections summary
    collections_query = select(
        func.coalesce(func.sum(Payment.amount), 0).label("total_collected"),
        func.count(Payment.id).label("payment_count"),
    ).where(
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date,
        Payment.status == PaymentStatus.CLEARED,
        Payment.deleted_at == None,
    )
    collections_result = await db.execute(collections_query)
    collections = collections_result.first()

    return {
        "period": {
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
        "summary": {
            "total_invoices": summary.total_invoices or 0,
            "total_revenue": float(summary.total_revenue or 0),
            "total_tax": float(summary.total_tax or 0),
            "total_transport": float(summary.total_transport or 0),
            "total_collected": float(collections.total_collected or 0),
            "payment_count": collections.payment_count or 0,
        },
        "by_product": [{
            "product_name": row.product_name,
            "sku": row.sku,
            "total_qty": int(row.total_qty),
            "total_amount": float(row.total_amount),
        } for row in product_sales],
        "by_customer": [{
            "id": str(row.id),
            "shop_name": row.shop_name,
            "name": row.name,
            "invoice_count": row.invoice_count,
            "total_amount": float(row.total_amount),
        } for row in customer_sales],
    }


@router.get("/inventory")
async def get_inventory_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Inventory valuation and aging report.
    """
    # 1. Product inventory with valuation
    products_query = select(Product).where(Product.deleted_at == None).order_by(Product.category, Product.name)
    result = await db.execute(products_query)
    products = result.scalars().all()

    today = date.today()
    total_stock_value = Decimal("0.00")
    total_mrp_value = Decimal("0.00")
    low_stock_items = []
    expired_items = []
    category_breakdown = {}

    product_rows = []
    for p in products:
        stock_value = Decimal(str(p.dealer_price)) * p.stock
        mrp_value = Decimal(str(p.mrp)) * p.stock
        total_stock_value += stock_value
        total_mrp_value += mrp_value

        is_expired = p.expiry_date < today if p.expiry_date else False
        days_to_expiry = (p.expiry_date - today).days if p.expiry_date else None

        if p.stock <= 50:
            low_stock_items.append({
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock,
            })

        if is_expired:
            expired_items.append({
                "name": p.name,
                "sku": p.sku,
                "expiry_date": str(p.expiry_date),
                "stock": p.stock,
            })

        # Category aggregation
        cat = p.category or "Uncategorized"
        if cat not in category_breakdown:
            category_breakdown[cat] = {"count": 0, "total_stock": 0, "total_value": Decimal("0.00")}
        category_breakdown[cat]["count"] += 1
        category_breakdown[cat]["total_stock"] += p.stock
        category_breakdown[cat]["total_value"] += stock_value

        product_rows.append({
            "id": str(p.id),
            "name": p.name,
            "sku": p.sku,
            "category": p.category,
            "batch_number": p.batch_number,
            "stock": p.stock,
            "dealer_price": float(p.dealer_price),
            "stock_value": float(stock_value),
            "expiry_date": str(p.expiry_date) if p.expiry_date else None,
            "days_to_expiry": days_to_expiry,
            "is_expired": is_expired,
        })

    return {
        "summary": {
            "total_products": len(products),
            "total_stock_value": float(total_stock_value),
            "total_mrp_value": float(total_mrp_value),
            "low_stock_count": len(low_stock_items),
            "expired_count": len(expired_items),
        },
        "by_category": [{
            "category": cat,
            "product_count": data["count"],
            "total_stock": data["total_stock"],
            "total_value": float(data["total_value"]),
        } for cat, data in category_breakdown.items()],
        "low_stock": low_stock_items,
        "expired": expired_items,
        "products": product_rows,
    }


@router.get("/outstanding")
async def get_outstanding_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Outstanding balances report - all customers with positive balances.
    """
    query = select(Customer).where(
        Customer.outstanding_balance > 0,
        Customer.deleted_at == None,
    ).order_by(Customer.outstanding_balance.desc())
    result = await db.execute(query)
    customers = result.scalars().all()

    total_outstanding = sum(float(c.outstanding_balance) for c in customers)

    return {
        "summary": {
            "total_outstanding": total_outstanding,
            "customer_count": len(customers),
        },
        "customers": [{
            "id": str(c.id),
            "name": c.name,
            "shop_name": c.shop_name,
            "phone": c.phone,
            "credit_limit": float(c.credit_limit),
            "outstanding_balance": float(c.outstanding_balance),
            "utilization_pct": round(float(c.outstanding_balance) / float(c.credit_limit) * 100, 1) if float(c.credit_limit) > 0 else 0,
        } for c in customers],
    }
