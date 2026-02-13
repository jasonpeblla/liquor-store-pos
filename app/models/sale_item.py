from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)  # Price at time of sale
    is_case_price = Column(Boolean, default=False)  # Whether case discount was applied
    discount_applied = Column(Float, default=0.0)
    line_total = Column(Float)
    
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")
