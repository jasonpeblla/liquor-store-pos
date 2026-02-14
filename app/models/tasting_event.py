# Tasting Events & Spirits Flights Model - FR-027
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class TastingEvent(Base):
    """In-store tasting events"""
    __tablename__ = "tasting_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Event info
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String, default="tasting")  # tasting, pairing, education, release
    category = Column(String, nullable=True)  # wine, whiskey, craft_beer, etc.
    
    # Scheduling
    event_date = Column(DateTime, nullable=False)
    start_time = Column(String, nullable=True)  # e.g., "18:00"
    end_time = Column(String, nullable=True)
    duration_minutes = Column(Integer, default=90)
    
    # Capacity
    max_attendees = Column(Integer, default=20)
    current_attendees = Column(Integer, default=0)
    
    # Pricing
    ticket_price = Column(Float, default=0.0)
    member_price = Column(Float, nullable=True)  # Wine/spirits club price
    
    # Products featured
    featured_products = Column(Text, nullable=True)  # Comma-separated product IDs
    
    # Status
    status = Column(String, default="scheduled")  # scheduled, in_progress, completed, cancelled
    
    # Host
    host_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    vendor_rep = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class TastingEventAttendee(Base):
    """Event attendees/registrations"""
    __tablename__ = "tasting_event_attendees"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("tasting_events.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Guest info (if no customer record)
    guest_name = Column(String, nullable=True)
    guest_email = Column(String, nullable=True)
    guest_phone = Column(String, nullable=True)
    
    # Registration
    ticket_type = Column(String, default="standard")  # standard, member, vip
    amount_paid = Column(Float, default=0.0)
    payment_status = Column(String, default="pending")  # pending, paid, refunded
    
    # Attendance
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    
    registered_at = Column(DateTime, default=datetime.utcnow)


class SpiritsFlight(Base):
    """Pre-configured spirits flights for tasting"""
    __tablename__ = "spirits_flights"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    flight_type = Column(String, default="whiskey")  # whiskey, tequila, rum, scotch, etc.
    
    # Products in flight (comma-separated IDs)
    product_ids = Column(Text, nullable=False)
    pour_size_oz = Column(Float, default=0.5)
    
    # Pricing
    price = Column(Float, nullable=False)
    member_price = Column(Float, nullable=True)
    
    # Availability
    is_active = Column(Boolean, default=True)
    available_start = Column(DateTime, nullable=True)  # Seasonal availability
    available_end = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
