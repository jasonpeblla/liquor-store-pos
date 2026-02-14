from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Time, ForeignKey, JSON
from datetime import datetime
from app.database import Base


class HappyHour(Base):
    """Time-based pricing rules for happy hour discounts"""
    __tablename__ = "happy_hours"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Weekday Happy Hour", "Sunday Funday"
    
    # Schedule (store as 24-hour time strings for SQLite compatibility)
    start_time = Column(String, nullable=False)  # e.g., "16:00"
    end_time = Column(String, nullable=False)    # e.g., "19:00"
    
    # Days of week (0=Monday, 6=Sunday)
    monday = Column(Boolean, default=False)
    tuesday = Column(Boolean, default=False)
    wednesday = Column(Boolean, default=False)
    thursday = Column(Boolean, default=False)
    friday = Column(Boolean, default=False)
    saturday = Column(Boolean, default=False)
    sunday = Column(Boolean, default=False)
    
    # Discount configuration
    discount_type = Column(String, default="percentage")  # percentage, fixed, price
    discount_value = Column(Float, default=10.0)  # 10% off, $2 off, or $5 fixed price
    
    # Scope
    applies_to = Column(String, default="all")  # all, category, product
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    product_ids = Column(JSON, nullable=True)  # List of specific product IDs
    
    # Restrictions
    max_quantity_per_customer = Column(Integer, nullable=True)  # Limit per transaction
    min_purchase = Column(Float, default=0.0)  # Minimum cart total
    exclude_case_pricing = Column(Boolean, default=True)  # Don't stack with case discounts
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
