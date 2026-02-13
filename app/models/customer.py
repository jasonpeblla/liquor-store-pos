from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    id_verified = Column(Boolean, default=False)
    id_verified_at = Column(DateTime, nullable=True)
    
    # Loyalty
    loyalty_points = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sales = relationship("Sale", back_populates="customer")
