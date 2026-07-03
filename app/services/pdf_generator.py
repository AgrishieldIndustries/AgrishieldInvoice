import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

from app.models.invoice import Invoice
from app.models.customer import Customer
from app.models.company_settings import CompanySettings

def generate_invoice_pdf(invoice: Invoice, customer: Customer, company: CompanySettings) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Define custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#16A34A')
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    company_style = ParagraphStyle(
        'CompanyDetails',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#475569')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )
    th_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    tb_style = ParagraphStyle(
        'TableBody',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#334155')
    )
    tb_style_right = ParagraphStyle(
        'TableBodyRight',
        parent=tb_style,
        alignment=TA_RIGHT
    )
    total_label_style = ParagraphStyle(
        'TotalLabel',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569')
    )
    total_val_style = ParagraphStyle(
        'TotalVal',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#1E293B'),
        alignment=TA_RIGHT
    )

    # 1. Header Table (Company Info Left, Document Title Right)
    header_left = [
        Paragraph(company.company_name, title_style),
        Spacer(1, 4),
        Paragraph(f"<b>Address:</b> {company.address}", company_style),
        Paragraph(f"<b>GSTIN:</b> {company.gstin} | <b>Phone:</b> {company.phone}", company_style),
        Paragraph(f"<b>Email:</b> {company.email}", company_style),
    ]

    header_right = [
        Paragraph("TAX INVOICE", ParagraphStyle('TaxInvoice', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#1E293B'), alignment=TA_RIGHT)),
        Spacer(1, 10),
        Table([
            [Paragraph("Invoice No:", meta_label), Paragraph(invoice.invoice_number, meta_val)],
            [Paragraph("Invoice Date:", meta_label), Paragraph(invoice.invoice_date.strftime("%d-%b-%Y"), meta_val)],
            [Paragraph("Payment Terms:", meta_label), Paragraph(invoice.terms or "Due on Receipt", meta_val)]
        ], colWidths=[80, 80], style=[
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ])
    ]

    header_table = Table([[header_left, header_right]], colWidths=[340, 180])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))

    # 2. Billing details (Billed To Left, Supply details Right)
    billing_left = [
        Paragraph("BILLED TO", section_heading),
        Spacer(1, 4),
        Paragraph(f"<b>Shop Name:</b> {customer.shop_name}", meta_val),
        Paragraph(f"<b>Proprietor:</b> {customer.name}", meta_val),
        Paragraph(f"<b>GSTIN:</b> {customer.gstin or 'N/A'}", meta_val),
        Paragraph(f"<b>Phone:</b> {customer.phone}", meta_val),
        Paragraph(f"<b>Billing Address:</b> {customer.billing_address}", company_style),
    ]

    # Maharashtra is state code 27
    state_supply = "Within Maharashtra" if (customer.gstin and customer.gstin.startswith("27")) else "Outside Maharashtra"
    billing_right = [
        Paragraph("TRANSPORT & SUPPLY", section_heading),
        Spacer(1, 4),
        Paragraph(f"<b>Place of Supply:</b> {customer.shipping_address.split(',')[0]}", meta_val),
        Paragraph(f"<b>State of Supply:</b> {customer.shipping_address.split(',')[-2] if ',' in customer.shipping_address else 'Maharashtra'}", meta_val),
        Paragraph(f"<b>Transport Charges:</b> ₹{invoice.transport_charges:,.2f}", meta_val),
        Paragraph(f"<b>Taxation Method:</b> {'IGST (Inter-state)' if invoice.igst_total > 0 else 'CGST + SGST (Intra-state)'}", meta_val),
    ]

    billing_table = Table([[billing_left, billing_right]], colWidths=[260, 260])
    billing_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(billing_table)
    story.append(Spacer(1, 15))

    # 3. Product table headers
    table_data = [[
        Paragraph("<b>#</b>", th_style),
        Paragraph("<b>Product Description</b>", th_style),
        Paragraph("<b>HSN</b>", th_style),
        Paragraph("<b>Qty</b>", th_style),
        Paragraph("<b>Rate (₹)</b>", th_style),
        Paragraph("<b>Disc %</b>", th_style),
        Paragraph("<b>Taxable Value (₹)</b>", th_style),
        Paragraph("<b>GST %</b>", th_style),
        Paragraph("<b>GST (₹)</b>", th_style),
        Paragraph("<b>Total (₹)</b>", th_style)
    ]]

    # Fill items
    for idx, item in enumerate(invoice.items, 1):
        gst_amt = float(item.cgst_amount + item.sgst_amount + item.igst_amount)
        table_data.append([
            Paragraph(str(idx), tb_style),
            Paragraph(f"<b>{item.product_name}</b><br/>SKU: {item.sku}", tb_style),
            Paragraph(item.sku.split('-')[-1] if '-' in item.sku else '3105', tb_style), # dummy HSN fallback
            Paragraph(str(item.quantity), tb_style_right),
            Paragraph(f"{float(item.rate):,.2f}", tb_style_right),
            Paragraph(f"{float(item.discount_pct):.1f}%", tb_style_right),
            Paragraph(f"{float(item.subtotal):,.2f}", tb_style_right),
            Paragraph(f"{float(item.gst_rate):.1f}%", tb_style_right),
            Paragraph(f"{gst_amt:,.2f}", tb_style_right),
            Paragraph(f"{float(item.total_amount):,.2f}", tb_style_right),
        ])

    prod_table = Table(table_data, colWidths=[20, 150, 40, 30, 45, 35, 55, 35, 45, 65])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#16A34A')),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 15))

    # 4. Summary & Terms Block
    # Bank Details Left, Totals Right
    bank_details_block = [
        Paragraph("BANK DETAILS & SETTLEMENT", section_heading),
        Spacer(1, 4),
        Paragraph(f"<b>Bank Name:</b> {company.bank_name}", company_style),
        Paragraph(f"<b>A/C Name:</b> {company.company_name}", company_style),
        Paragraph(f"<b>Account No:</b> {company.bank_account_no}", company_style),
        Paragraph(f"<b>IFSC Code:</b> {company.bank_ifsc}", company_style),
        Spacer(1, 8),
        Paragraph("<b>Terms & Conditions:</b>", company_style),
        Paragraph(company.terms_and_conditions.replace("\n", "<br/>"), company_style)
    ]

    totals_data = [
        [Paragraph("Taxable Subtotal:", total_label_style), Paragraph(f"₹{invoice.subtotal:,.2f}", total_val_style)],
    ]
    if invoice.cgst_total > 0:
        totals_data.append([Paragraph("CGST Total:", total_label_style), Paragraph(f"₹{invoice.cgst_total:,.2f}", total_val_style)])
        totals_data.append([Paragraph("SGST Total:", total_label_style), Paragraph(f"₹{invoice.sgst_total:,.2f}", total_val_style)])
    if invoice.igst_total > 0:
        totals_data.append([Paragraph("IGST Total:", total_label_style), Paragraph(f"₹{invoice.igst_total:,.2f}", total_val_style)])
    
    totals_data.append([Paragraph("Transport / Loading:", total_label_style), Paragraph(f"₹{invoice.transport_charges:,.2f}", total_val_style)])
    totals_data.append([Paragraph("Grand Total:", ParagraphStyle('GTL', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#16A34A'))), Paragraph(f"₹{invoice.grand_total:,.2f}", ParagraphStyle('GTV', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#16A34A'), alignment=TA_RIGHT))])

    totals_table = Table(totals_data, colWidths=[110, 90])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,-1), (-1,-1), 1, colors.HexColor('#16A34A')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F0FDF4')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#F1F5F9')),
    ]))

    summary_block = Table([[bank_details_block, totals_table]], colWidths=[310, 210])
    summary_block.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(KeepTogether([
        summary_block,
        Spacer(1, 25),
        # Signatures
        Table([
            [Paragraph("", meta_val), Paragraph("For <b>" + company.company_name + "</b>", ParagraphStyle('FCN', fontName='Helvetica', fontSize=8.5, alignment=TA_RIGHT))],
            [Spacer(1, 35), Spacer(1, 35)],
            [Paragraph("Customer Signature", ParagraphStyle('CS', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#64748B'))), Paragraph("Authorized Signatory", ParagraphStyle('AS', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#64748B'), alignment=TA_RIGHT))]
        ], colWidths=[260, 260], style=[
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ])
    ]))

    doc.build(story)
    buffer.seek(0)
    return buffer
