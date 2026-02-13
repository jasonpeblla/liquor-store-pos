from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    brand = Column(String, index=True, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    sku = Column(String, unique=True, index=True, nullable=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    
    # Pricing
    price = Column(Float)
    case_price = Column(Float, nullable=True)  # Price when buying a full case
    case_size = Column(Integer, default=12)  # Units per case
    
    # Inventory
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    
    # Product details
    size = Column(String, nullable=True)  # e.g., "750ml", "1L", "6-pack"
    abv = Column(Float, nullable=True)  # Alcohol by volume percentage
    description = Column(String, nullable=True)
    
    # Flags
    is_active = Column(Boolean, default=True)
    requires_age_verification = Column(Boolean, default=True)
    
    # Stats
    times_sold = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = relationship("Category", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")
