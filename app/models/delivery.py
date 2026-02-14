# Delivery & Curbside Model - FR-028
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class DeliveryOrder(Base):
    """Delivery and curbside pickup orders"""
    __tablename__ = "delivery_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Order type
    order_type = Column(String, default="delivery")  # delivery, curbside
    
    # Delivery address
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    delivery_instructions = Column(Text, nullable=True)
    
    # Scheduling
    requested_date = Column(DateTime, nullable=True)
    requested_time_slot = Column(String, nullable=True)  # e.g., "14:00-16:00"
    
    # Curbside specific
    vehicle_description = Column(String, nullable=True)
    parking_spot = Column(String, nullable=True)
    
    # Fees
    delivery_fee = Column(Float, default=0.0)
    tip_amount = Column(Float, default=0.0)
    
    # Status
    status = Column(String, default="pending")  # pending, confirmed, preparing, out_for_delivery, delivered, cancelled
    
    # Assignment
    driver_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Tracking
    picked_up_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Age verification at delivery
    age_verified_at_delivery = Column(Boolean, default=False)
    id_type_verified = Column(String, nullable=True)
    verifier_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryZone(Base):
    """Delivery zones and fees"""
    __tablename__ = "delivery_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    
    zone_name = Column(String, nullable=False)
    zip_codes = Column(Text, nullable=True)  # Comma-separated
    
    # Fees
    delivery_fee = Column(Float, default=0.0)
    minimum_order = Column(Float, default=0.0)
    free_delivery_threshold = Column(Float, nullable=True)
    
    # Availability
    is_active = Column(Boolean, default=True)
    max_daily_orders = Column(Integer, nullable=True)
    
    # Time windows
    available_days = Column(String, default="Mon,Tue,Wed,Thu,Fri,Sat,Sun")
    start_time = Column(String, default="10:00")
    end_time = Column(String, default="20:00")
