from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
from app.database import Base


class Reservation(Base):
    """Product reservations and pre-orders"""
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    reservation_number = Column(String, unique=True, index=True)  # R-YYYYMMDD-001
    
    # Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String, nullable=False)  # For walk-ins without account
    customer_phone = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    
    # Product
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)  # Price at time of reservation
    
    # Deposit
    deposit_amount = Column(Float, default=0.0)
    deposit_paid = Column(Boolean, default=False)
    deposit_payment_method = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, confirmed, ready, picked_up, cancelled, expired
    
    # Dates
    requested_date = Column(DateTime, nullable=True)  # When customer wants it
    expected_date = Column(DateTime, nullable=True)   # When we expect stock
    pickup_by_date = Column(DateTime, nullable=True)  # Must pick up by
    picked_up_at = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Staff
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
