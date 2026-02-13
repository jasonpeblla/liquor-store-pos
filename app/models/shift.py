from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.database import Base


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    cashier_name = Column(String, index=True)
    
    # Shift timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Cash management
    opening_cash = Column(Float, default=0.0)
    closing_cash = Column(Float, nullable=True)
    expected_cash = Column(Float, nullable=True)
    cash_variance = Column(Float, nullable=True)
    
    # Shift stats (updated on close)
    total_sales = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_cash_sales = Column(Float, default=0.0)
    total_card_sales = Column(Float, default=0.0)
    
    # Age verifications performed
    age_verifications_count = Column(Integer, default=0)
    age_verifications_declined = Column(Integer, default=0)
    
    notes = Column(String, nullable=True)
