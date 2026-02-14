# Store Hours - FR-035
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class StoreHours(Base):
    """Regular store operating hours"""
    __tablename__ = "store_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    day_name = Column(String, nullable=False)
    
    is_open = Column(Boolean, default=True)
    open_time = Column(String, nullable=True)  # "09:00"
    close_time = Column(String, nullable=True)  # "21:00"
    
    # Alcohol sales hours (may differ from store hours)
    alcohol_open_time = Column(String, nullable=True)
    alcohol_close_time = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HolidayHours(Base):
    """Holiday and special hours"""
    __tablename__ = "holiday_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    
    date = Column(DateTime, nullable=False)
    name = Column(String, nullable=False)  # e.g., "Thanksgiving", "New Year's Eve"
    
    is_closed = Column(Boolean, default=False)
    open_time = Column(String, nullable=True)
    close_time = Column(String, nullable=True)
    
    # Alcohol sales
    alcohol_open_time = Column(String, nullable=True)
    alcohol_close_time = Column(String, nullable=True)
    
    note = Column(String, nullable=True)  # e.g., "Closing early"
    
    created_at = Column(DateTime, default=datetime.utcnow)


class AlcoholSaleRestriction(Base):
    """State/local alcohol sale time restrictions"""
    __tablename__ = "alcohol_sale_restrictions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Day restrictions
    restricted_days = Column(String, nullable=True)  # e.g., "Sunday" or "0,6" (Mon, Sun)
    
    # Time restrictions
    restricted_start = Column(String, nullable=True)  # "02:00"
    restricted_end = Column(String, nullable=True)  # "06:00"
    
    # Categories affected (null = all alcohol)
    category_ids = Column(String, nullable=True)  # Comma-separated
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
