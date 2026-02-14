# Spirits Profile & Customer Preferences - FR-029
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class CustomerTasteProfile(Base):
    """Customer taste preferences for personalized recommendations"""
    __tablename__ = "customer_taste_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    
    # Wine preferences
    prefers_red = Column(Boolean, default=False)
    prefers_white = Column(Boolean, default=False)
    prefers_sparkling = Column(Boolean, default=False)
    prefers_rose = Column(Boolean, default=False)
    wine_sweetness = Column(String, nullable=True)  # dry, off-dry, sweet
    wine_body = Column(String, nullable=True)  # light, medium, full
    
    # Spirits preferences
    prefers_whiskey = Column(Boolean, default=False)
    prefers_vodka = Column(Boolean, default=False)
    prefers_gin = Column(Boolean, default=False)
    prefers_rum = Column(Boolean, default=False)
    prefers_tequila = Column(Boolean, default=False)
    prefers_brandy = Column(Boolean, default=False)
    
    # Beer preferences
    prefers_lager = Column(Boolean, default=False)
    prefers_ale = Column(Boolean, default=False)
    prefers_ipa = Column(Boolean, default=False)
    prefers_stout = Column(Boolean, default=False)
    prefers_sour = Column(Boolean, default=False)
    
    # Price range
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    
    # Dietary
    prefers_organic = Column(Boolean, default=False)
    prefers_biodynamic = Column(Boolean, default=False)
    gluten_free = Column(Boolean, default=False)
    
    # Flavor notes liked
    flavor_notes = Column(Text, nullable=True)  # Comma-separated
    
    # Regions of interest
    favorite_regions = Column(Text, nullable=True)  # Comma-separated
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductRecommendation(Base):
    """Personalized product recommendations"""
    __tablename__ = "product_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    reason = Column(String, nullable=True)  # Why this was recommended
    score = Column(Float, default=0.0)  # Relevance score
    
    # Status
    status = Column(String, default="active")  # active, viewed, purchased, dismissed
    viewed_at = Column(DateTime, nullable=True)
    purchased_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
