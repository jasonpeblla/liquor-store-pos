from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from datetime import datetime
from app.database import Base


class TastingNote(Base):
    """Staff tasting notes and product descriptions"""
    __tablename__ = "tasting_notes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Tasting profile
    nose = Column(Text, nullable=True)  # Aroma/smell
    palate = Column(Text, nullable=True)  # Taste
    finish = Column(Text, nullable=True)  # Aftertaste
    
    # Wine-specific
    vintage = Column(Integer, nullable=True)  # Year
    region = Column(String, nullable=True)  # e.g., Napa Valley, Bordeaux
    grape_variety = Column(String, nullable=True)  # e.g., Cabernet Sauvignon
    
    # Ratings (1-5 scale)
    staff_rating = Column(Float, nullable=True)
    
    # Food pairings
    food_pairings = Column(JSON, nullable=True)  # ["steak", "cheese", "chocolate"]
    
    # Serving suggestions
    serve_temp = Column(String, nullable=True)  # e.g., "Chilled", "Room temp", "55-60°F"
    decant_time = Column(String, nullable=True)  # e.g., "30 minutes", "1 hour"
    glass_type = Column(String, nullable=True)  # e.g., "Bordeaux glass", "Flute"
    
    # General notes
    description = Column(Text, nullable=True)
    staff_pick = Column(Boolean, default=False)
    
    # Meta
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductReview(Base):
    """Customer reviews and ratings"""
    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String, nullable=True)
    review_text = Column(Text, nullable=True)
    
    # Verification
    verified_purchase = Column(Boolean, default=False)
    
    # Moderation
    is_approved = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Helpfulness
    helpful_votes = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
