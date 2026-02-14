# Cash Drawer Management - FR-032
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class CashDrawer(Base):
    """Cash drawer sessions"""
    __tablename__ = "cash_drawers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Session info
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    register_number = Column(Integer, default=1)
    
    # Opening
    opened_at = Column(DateTime, default=datetime.utcnow)
    opening_amount = Column(Float, nullable=False)
    opening_verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Closing
    closed_at = Column(DateTime, nullable=True)
    expected_amount = Column(Float, nullable=True)
    actual_amount = Column(Float, nullable=True)
    variance = Column(Float, nullable=True)
    closing_verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Status
    status = Column(String, default="open")  # open, closed, suspended
    
    # Denominations at close (JSON)
    denomination_breakdown = Column(Text, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CashMovement(Base):
    """Track cash movements (drops, pickups, paid-outs)"""
    __tablename__ = "cash_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    drawer_id = Column(Integer, ForeignKey("cash_drawers.id"), nullable=False)
    
    movement_type = Column(String, nullable=False)  # drop, pickup, paid_out, paid_in, no_sale
    amount = Column(Float, nullable=False)
    
    # Authorization
    performed_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    authorized_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    reason = Column(String, nullable=True)
    reference = Column(String, nullable=True)  # e.g., safe drop #, vendor name
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SafeDrop(Base):
    """Safe drops from registers"""
    __tablename__ = "safe_drops"
    
    id = Column(Integer, primary_key=True, index=True)
    
    drawer_id = Column(Integer, ForeignKey("cash_drawers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    
    dropped_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    verified_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    drop_number = Column(String, nullable=True)  # Envelope or bag number
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
