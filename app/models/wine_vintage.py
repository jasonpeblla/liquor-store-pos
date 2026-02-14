# Wine Vintage Model - FR-024
# Track vintage years, ratings, and cellaring recommendations

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class WineVintage(Base):
    """Wine vintage information for wine products"""
    __tablename__ = "wine_vintages"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Vintage info
    vintage_year = Column(Integer, nullable=False)
    region = Column(String, nullable=True)
    appellation = Column(String, nullable=True)
    vineyard = Column(String, nullable=True)
    
    # Ratings
    critic_score = Column(Float, nullable=True)  # e.g., 92/100
    critic_source = Column(String, nullable=True)  # e.g., "Wine Spectator"
    house_rating = Column(Float, nullable=True)  # Store's own rating
    
    # Characteristics
    grape_varieties = Column(String, nullable=True)  # Comma-separated
    aging_potential = Column(String, nullable=True)  # e.g., "5-10 years"
    drink_window_start = Column(Integer, nullable=True)  # Year
    drink_window_end = Column(Integer, nullable=True)  # Year
    
    # Stock specific to this vintage
    vintage_stock = Column(Integer, default=0)
    vintage_price = Column(Float, nullable=True)  # Override product price
    
    # Status
    is_allocated = Column(Boolean, default=False)  # Limited allocation
    is_library = Column(Boolean, default=False)  # Library/rare selection
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WineClubMember(Base):
    """Wine club membership for special allocations"""
    __tablename__ = "wine_club_members"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Membership
    membership_tier = Column(String, default="basic")  # basic, premium, reserve
    join_date = Column(DateTime, default=datetime.utcnow)
    renewal_date = Column(DateTime, nullable=True)
    
    # Preferences
    red_preference = Column(Boolean, default=True)
    white_preference = Column(Boolean, default=True)
    sparkling_preference = Column(Boolean, default=False)
    bottles_per_shipment = Column(Integer, default=2)
    
    # Status
    is_active = Column(Boolean, default=True)
    allocation_priority = Column(Integer, default=1)  # Higher = first access
    
    total_purchases = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
