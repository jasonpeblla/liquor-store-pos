from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    
    # Type: percentage, fixed_amount, buy_x_get_y
    promo_type = Column(String, default="percentage")
    
    # Discount value (percentage or fixed amount)
    discount_value = Column(Float)
    
    # For buy X get Y deals
    buy_quantity = Column(Integer, nullable=True)
    get_quantity = Column(Integer, nullable=True)
    
    # Scope: all, category, product
    scope = Column(String, default="all")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    # Minimum purchase requirement
    min_purchase = Column(Float, default=0.0)
    
    # Validity
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Usage limits
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
