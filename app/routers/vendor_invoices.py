# Vendor Invoices Router - FR-037
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.vendor_invoice import VendorInvoice, VendorInvoiceItem, VendorPayment

router = APIRouter(prefix="/vendor-invoices", tags=["vendor-invoices"])


class InvoiceItemCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: int
    unit_cost: float


class InvoiceCreate(BaseModel):
    supplier_id: int
    purchase_order_id: Optional[int] = None
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime] = None
    tax_amount: float = 0
    shipping_amount: float = 0
    payment_terms: Optional[str] = None
    items: List[InvoiceItemCreate]


class PaymentCreate(BaseModel):
    amount: float
    payment_method: str
    reference_number: Optional[str] = None


@router.post("/")
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a vendor invoice"""
    # Calculate totals
    subtotal = sum(item.quantity * item.unit_cost for item in invoice.items)
    total = subtotal + invoice.tax_amount + invoice.shipping_amount
    
    db_invoice = VendorInvoice(
        supplier_id=invoice.supplier_id,
        purchase_order_id=invoice.purchase_order_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        subtotal=subtotal,
        tax_amount=invoice.tax_amount,
        shipping_amount=invoice.shipping_amount,
        total_amount=total,
        payment_terms=invoice.payment_terms
    )
    db.add(db_invoice)
    db.flush()
    
    # Add line items
    for item in invoice.items:
        db_item = VendorInvoiceItem(
            invoice_id=db_invoice.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            total_cost=item.quantity * item.unit_cost
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@router.get("/")
def list_invoices(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List vendor invoices"""
    query = db.query(VendorInvoice)
    if status:
        query = query.filter(VendorInvoice.status == status)
    if payment_status:
        query = query.filter(VendorInvoice.payment_status == payment_status)
    if supplier_id:
        query = query.filter(VendorInvoice.supplier_id == supplier_id)
    return query.order_by(desc(VendorInvoice.invoice_date)).all()


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get invoice with items"""
    invoice = db.query(VendorInvoice).filter(VendorInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    items = db.query(VendorInvoiceItem).filter(VendorInvoiceItem.invoice_id == invoice_id).all()
    payments = db.query(VendorPayment).filter(VendorPayment.invoice_id == invoice_id).all()
    
    return {
        "invoice": invoice,
        "items": items,
        "payments": payments,
        "balance_due": invoice.total_amount - invoice.amount_paid
    }


@router.post("/{invoice_id}/verify-item/{item_id}")
def verify_item(invoice_id: int, item_id: int, quantity_received: int, db: Session = Depends(get_db)):
    """Verify received quantity for line item"""
    item = db.query(VendorInvoiceItem).filter(
        VendorInvoiceItem.id == item_id,
        VendorInvoiceItem.invoice_id == invoice_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.quantity_received = quantity_received
    item.is_verified = True
    db.commit()
    
    discrepancy = item.quantity - quantity_received
    return {
        "verified": True,
        "expected": item.quantity,
        "received": quantity_received,
        "discrepancy": discrepancy
    }


@router.post("/{invoice_id}/pay")
def record_payment(invoice_id: int, payment: PaymentCreate, db: Session = Depends(get_db)):
    """Record a payment on invoice"""
    invoice = db.query(VendorInvoice).filter(VendorInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db_payment = VendorPayment(
        invoice_id=invoice_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        reference_number=payment.reference_number
    )
    db.add(db_payment)
    
    invoice.amount_paid += payment.amount
    if invoice.amount_paid >= invoice.total_amount:
        invoice.payment_status = "paid"
    else:
        invoice.payment_status = "partial"
    
    db.commit()
    
    return {
        "payment_recorded": True,
        "amount": payment.amount,
        "balance_due": invoice.total_amount - invoice.amount_paid
    }


@router.get("/payables/summary")
def accounts_payable_summary(db: Session = Depends(get_db)):
    """Get accounts payable summary"""
    total_outstanding = db.query(func.sum(VendorInvoice.total_amount - VendorInvoice.amount_paid)).filter(
        VendorInvoice.payment_status != "paid"
    ).scalar() or 0
    
    overdue = db.query(VendorInvoice).filter(
        VendorInvoice.due_date < datetime.utcnow(),
        VendorInvoice.payment_status != "paid"
    ).all()
    
    overdue_amount = sum(i.total_amount - i.amount_paid for i in overdue)
    
    return {
        "total_outstanding": float(total_outstanding),
        "overdue_count": len(overdue),
        "overdue_amount": float(overdue_amount)
    }
