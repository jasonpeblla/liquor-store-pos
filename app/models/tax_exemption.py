# Tax Exemption - FR-033
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class TaxExemptCustomer(Base):
    """Tax exempt customer records"""
    __tablename__ = "tax_exempt_customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Exemption details
    exemption_type = Column(String, nullable=False)  # resale, nonprofit, government, diplomatic
    certificate_number = Column(String, nullable=False)
    issuing_state = Column(String, nullable=True)
    
    # Categories exempt (null = all)
    exempt_categories = Column(Text, nullable=True)  # Comma-separated category IDs
    
    # Validity
    effective_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    
    # Documentation
    certificate_on_file = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaxExemptSale(Base):
    """Tax exempt sale records"""
    __tablename__ = "tax_exempt_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    exemption_id = Column(Integer, ForeignKey("tax_exempt_customers.id"), nullable=False)
    
    tax_exempted = Column(Float, nullable=False)  # Amount of tax exempted
    exemption_type = Column(String, nullable=False)
    certificate_number = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
