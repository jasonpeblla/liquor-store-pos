# Audit Log - FR-038
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime
from app.database import Base


class AuditLog(Base):
    """System audit log for compliance and security"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Action details
    action = Column(String, nullable=False)  # e.g., sale_complete, refund, void, price_change
    entity_type = Column(String, nullable=False)  # e.g., sale, product, customer, employee
    entity_id = Column(Integer, nullable=True)
    
    # Who/what
    user_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    user_type = Column(String, default="employee")  # employee, system, api
    
    # Details
    old_value = Column(Text, nullable=True)  # JSON of previous state
    new_value = Column(Text, nullable=True)  # JSON of new state
    description = Column(Text, nullable=True)
    
    # Context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    register_number = Column(Integer, nullable=True)
    
    # Compliance flags
    is_sensitive = Column(String, default="no")  # no, moderate, high
    requires_review = Column(String, default="no")  # no, yes, reviewed
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PriceChangeLog(Base):
    """Specific log for price changes (regulatory compliance)"""
    __tablename__ = "price_change_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=True)
    
    changed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reason = Column(String, nullable=True)
    
    effective_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    """Track login attempts"""
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    username = Column(String, nullable=True)
    
    success = Column(String, default="no")
    failure_reason = Column(String, nullable=True)
    
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
