from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base


class QuantityLimit(Base):
    """Purchase quantity limits for products or categories"""
    __tablename__ = "quantity_limits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Spirits Daily Limit"
    
    # Scope - can apply to product, category, or all alcohol
    limit_type = Column(String, default="category")  # category, product, alcohol
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    # Limits
    per_transaction = Column(Integer, nullable=True)  # Max per single transaction
    per_day = Column(Integer, nullable=True)  # Max per day per customer
    per_week = Column(Integer, nullable=True)  # Max per week per customer
    
    # Actions when exceeded
    action = Column(String, default="block")  # block, warn, require_manager
    warning_message = Column(String, nullable=True)
    
    # Requires ID check above this quantity
    id_required_above = Column(Integer, nullable=True)
    
    # State compliance (some states have specific limits)
    state_code = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuantityLimitViolation(Base):
    """Log of quantity limit violations for compliance tracking"""
    __tablename__ = "quantity_limit_violations"

    id = Column(Integer, primary_key=True, index=True)
    
    limit_id = Column(Integer, ForeignKey("quantity_limits.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Violation details
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    requested_quantity = Column(Integer, nullable=False)
    allowed_quantity = Column(Integer, nullable=False)
    
    # Resolution
    action_taken = Column(String, nullable=False)  # blocked, reduced, manager_override
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    override_reason = Column(String, nullable=True)
    
    # Context
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
