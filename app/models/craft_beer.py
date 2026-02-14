# Craft Beer & Keg Tracking Model - FR-025
# Track kegs, growler fills, and tap rotation

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Keg(Base):
    """Track kegs for tap/growler stations"""
    __tablename__ = "kegs"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    
    # Keg info
    keg_size = Column(String, default="1/2")  # 1/6, 1/4, 1/2, etc.
    capacity_oz = Column(Float, default=1984)  # 1/2 barrel = 1984 oz
    remaining_oz = Column(Float, default=1984)
    
    # Cost/pricing
    keg_cost = Column(Float, default=0.0)
    price_per_oz = Column(Float, default=0.0)
    growler_32_price = Column(Float, default=0.0)
    growler_64_price = Column(Float, default=0.0)
    pint_price = Column(Float, default=0.0)
    taster_price = Column(Float, default=0.0)  # 4oz sample
    
    # Tap assignment
    tap_number = Column(Integer, nullable=True)
    tapped_date = Column(DateTime, nullable=True)
    projected_empty_date = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default="in_stock")  # in_stock, on_tap, kicked, returned
    
    # Deposit tracking
    deposit_amount = Column(Float, default=0.0)
    deposit_paid = Column(Boolean, default=False)
    deposit_returned = Column(Boolean, default=False)
    
    # Beer details for tap list
    style = Column(String, nullable=True)
    ibu = Column(Integer, nullable=True)
    abv = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GrowlerFill(Base):
    """Track growler fill sales"""
    __tablename__ = "growler_fills"
    
    id = Column(Integer, primary_key=True, index=True)
    keg_id = Column(Integer, ForeignKey("kegs.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Fill details
    size_oz = Column(Float, nullable=False)  # 32, 64, 128, etc.
    price = Column(Float, nullable=False)
    
    # Growler type
    container_type = Column(String, default="house")  # house, customer, can, etc.
    is_refill = Column(Boolean, default=False)
    
    filled_at = Column(DateTime, default=datetime.utcnow)
    filled_by = Column(Integer, nullable=True)  # Employee ID


class TapRotation(Base):
    """Track tap rotation history and planning"""
    __tablename__ = "tap_rotations"
    
    id = Column(Integer, primary_key=True, index=True)
    tap_number = Column(Integer, nullable=False)
    keg_id = Column(Integer, ForeignKey("kegs.id"), nullable=False)
    
    # Timing
    tapped_at = Column(DateTime, default=datetime.utcnow)
    kicked_at = Column(DateTime, nullable=True)
    
    # Performance
    total_pours = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    days_on_tap = Column(Integer, default=0)
    
    notes = Column(Text, nullable=True)
