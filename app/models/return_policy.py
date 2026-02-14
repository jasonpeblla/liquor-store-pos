# Returns & Exchanges - FR-036
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class ReturnPolicy(Base):
    """Return policy rules"""
    __tablename__ = "return_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Time limits
    return_days = Column(Integer, default=30)
    exchange_days = Column(Integer, default=60)
    
    # Conditions
    requires_receipt = Column(Boolean, default=True)
    requires_unopened = Column(Boolean, default=True)
    restocking_fee_percent = Column(Float, default=0)
    
    # Refund type
    refund_type = Column(String, default="original")  # original, store_credit, exchange_only
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductReturn(Base):
    """Track product returns"""
    __tablename__ = "product_returns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    original_sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    refund_amount = Column(Float, nullable=False)
    
    return_reason = Column(String, nullable=False)  # defective, wrong_item, changed_mind, damaged, other
    condition = Column(String, default="unopened")  # unopened, opened, damaged
    
    # Refund details
    refund_method = Column(String, nullable=False)  # cash, card, store_credit
    restocking_fee = Column(Float, default=0)
    
    # Status
    status = Column(String, default="pending")  # pending, approved, completed, denied
    
    processed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Exchange(Base):
    """Product exchanges"""
    __tablename__ = "exchanges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    return_id = Column(Integer, ForeignKey("product_returns.id"), nullable=False)
    new_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    price_difference = Column(Float, default=0)  # Positive = customer pays, negative = refund
    
    created_at = Column(DateTime, default=datetime.utcnow)
