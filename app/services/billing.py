from app.models.customer import Customer
from app.models.product import Product

def calculate_taxes_for_item(
    quantity: int,
    rate: float,
    discount_pct: float,
    gst_rate: float,
    is_interstate: bool
):
    # Calculations
    subtotal = float(quantity) * float(rate) * (1.0 - (float(discount_pct) / 100.0))
    total_gst = subtotal * (float(gst_rate) / 100.0)

    if is_interstate:
        igst_amount = total_gst
        cgst_amount = 0.0
        sgst_amount = 0.0
    else:
        igst_amount = 0.0
        cgst_amount = total_gst / 2.0
        sgst_amount = total_gst / 2.0

    total_amount = subtotal + total_gst

    return {
        "subtotal": round(subtotal, 2),
        "cgst_amount": round(cgst_amount, 2),
        "sgst_amount": round(sgst_amount, 2),
        "igst_amount": round(igst_amount, 2),
        "total_amount": round(total_amount, 2)
    }

def check_is_interstate(customer: Customer) -> bool:
    if not customer.gstin:
        return False # Default to intra-state local sale if GSTIN is not provided
    # Maharashtra state code is "27"
    return not customer.gstin.strip().startswith("27")
