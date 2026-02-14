# Vendor Invoices - FR-037
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class VendorInvoice(Base):
    """Vendor/supplier invoices"""
    __tablename__ = "vendor_invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    
    # Invoice details
    invoice_number = Column(String, nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    
    # Amounts
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    shipping_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    
    # Payment
    payment_terms = Column(String, nullable=True)  # e.g., "Net 30"
    payment_status = Column(String, default="pending")  # pending, partial, paid, overdue
    amount_paid = Column(Float, default=0)
    
    # Status
    status = Column(String, default="received")  # received, verified, disputed, paid
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VendorInvoiceItem(Base):
    """Line items on vendor invoices"""
    __tablename__ = "vendor_invoice_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("vendor_invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    description = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # Verification
    quantity_received = Column(Integer, nullable=True)
    is_verified = Column(Boolean, default=False)


class VendorPayment(Base):
    """Payments to vendors"""
    __tablename__ = "vendor_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("vendor_invoices.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)  # check, ach, wire, credit
    reference_number = Column(String, nullable=True)
    
    paid_at = Column(DateTime, default=datetime.utcnow)
    processed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
