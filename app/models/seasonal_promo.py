# Seasonal Promotions - FR-040
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class SeasonalPromotion(Base):
    """Seasonal and holiday promotions"""
    __tablename__ = "seasonal_promotions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Season/occasion
    occasion = Column(String, nullable=False)  # new_year, valentines, st_patricks, memorial_day, july_4th, labor_day, halloween, thanksgiving, christmas, other
    
    # Dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Targeting
    category_ids = Column(Text, nullable=True)  # Comma-separated
    product_ids = Column(Text, nullable=True)  # Comma-separated, for specific products
    
    # Discount
    discount_type = Column(String, default="percent")  # percent, fixed, bogo
    discount_value = Column(Float, nullable=False)
    minimum_purchase = Column(Float, nullable=True)
    
    # Limits
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, default=0)
    
    # Display
    banner_text = Column(String, nullable=True)
    display_priority = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SeasonalBundle(Base):
    """Holiday gift bundles"""
    __tablename__ = "seasonal_bundles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    occasion = Column(String, nullable=False)
    
    # Products in bundle
    product_ids = Column(Text, nullable=False)  # Comma-separated
    
    # Pricing
    regular_price = Column(Float, nullable=False)  # Sum of individual prices
    bundle_price = Column(Float, nullable=False)
    savings = Column(Float, nullable=True)
    
    # Packaging
    includes_gift_wrap = Column(Boolean, default=False)
    includes_gift_bag = Column(Boolean, default=False)
    
    # Availability
    stock_quantity = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
