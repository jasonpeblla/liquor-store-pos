# Advanced Price Rules - FR-030
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class PriceRule(Base):
    """Dynamic pricing rules"""
    __tablename__ = "price_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Rule type
    rule_type = Column(String, nullable=False)  # volume, bundle, time_based, customer_type, seasonal
    
    # Conditions
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    min_quantity = Column(Integer, nullable=True)
    max_quantity = Column(Integer, nullable=True)
    customer_tier = Column(String, nullable=True)  # bronze, silver, gold, platinum
    
    # Discount
    discount_type = Column(String, default="percent")  # percent, fixed, price_override
    discount_value = Column(Float, nullable=False)
    
    # Time constraints
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    active_days = Column(String, nullable=True)  # Mon,Tue,Wed,etc.
    active_hours_start = Column(String, nullable=True)  # 09:00
    active_hours_end = Column(String, nullable=True)  # 21:00
    
    # Priority and stacking
    priority = Column(Integer, default=0)  # Higher = applied first
    stackable = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class VolumeDiscount(Base):
    """Volume-based pricing tiers"""
    __tablename__ = "volume_discounts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Tiers (JSON stored as text)
    # e.g., [{"min_qty": 6, "discount_percent": 10}, {"min_qty": 12, "discount_percent": 15}]
    tiers = Column(Text, nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BundlePrice(Base):
    """Bundle pricing (buy X and Y together)"""
    __tablename__ = "bundle_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Products in bundle (comma-separated IDs)
    product_ids = Column(Text, nullable=False)
    
    # Bundle pricing
    bundle_price = Column(Float, nullable=False)
    savings_display = Column(String, nullable=True)  # "Save $5!"
    
    # Status
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
