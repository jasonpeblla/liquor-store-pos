from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    code = Column(String, unique=True, index=True, nullable=True)  # Supplier code
    
    # Contact info
    contact_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Address
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    
    # Business details
    license_number = Column(String, nullable=True)  # Liquor license
    tax_id = Column(String, nullable=True)
    payment_terms = Column(String, default="Net 30")  # Net 30, Net 60, COD, etc.
    
    # Ordering
    minimum_order = Column(Float, default=0.0)  # Minimum order amount
    delivery_days = Column(String, nullable=True)  # e.g., "Mon,Wed,Fri"
    lead_time_days = Column(Integer, default=3)  # Days from order to delivery
    
    # Categories they supply
    supplies_beer = Column(Boolean, default=False)
    supplies_wine = Column(Boolean, default=False)
    supplies_spirits = Column(Boolean, default=False)
    supplies_other = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)  # Preferred supplier
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
