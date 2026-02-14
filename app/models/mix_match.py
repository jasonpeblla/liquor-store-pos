from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base


class MixMatchDeal(Base):
    """Mix-and-match deals like 'Mix any 6 wines for 10% off'"""
    __tablename__ = "mix_match_deals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Mix 6 Wines", "Build Your Own 12-Pack"
    description = Column(String, nullable=True)
    
    # Qualifying items
    category_ids = Column(JSON, nullable=True)  # List of category IDs that qualify
    product_ids = Column(JSON, nullable=True)   # Specific product IDs (if not category-based)
    brand_filter = Column(String, nullable=True)  # Filter by brand (optional)
    min_price = Column(Float, nullable=True)     # Min price per item to qualify
    max_price = Column(Float, nullable=True)     # Max price per item to qualify
    
    # Quantity requirements
    quantity_required = Column(Integer, nullable=False)  # e.g., 6, 12
    
    # Discount configuration
    discount_type = Column(String, default="percentage")  # percentage, fixed_per_item, fixed_total
    discount_value = Column(Float, nullable=False)  # 10 for 10%, $2 per item, or $5 total off
    
    # Stacking rules
    stackable = Column(Boolean, default=False)  # Can combine with other discounts
    max_applications = Column(Integer, nullable=True)  # Max times deal can apply (e.g., buy 12 = 2x deal)
    
    # Date range (optional)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority deals apply first
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
