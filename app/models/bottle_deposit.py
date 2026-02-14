from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class BottleDepositConfig(Base):
    """Configuration for bottle deposits by container type"""
    __tablename__ = "bottle_deposit_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Glass Bottle", "Aluminum Can"
    container_type = Column(String, nullable=False)  # glass, aluminum, plastic
    size_min_oz = Column(Float, nullable=True)  # Min size (ounces)
    size_max_oz = Column(Float, nullable=True)  # Max size (ounces)
    deposit_amount = Column(Float, nullable=False)  # Deposit per container
    is_active = Column(Boolean, default=True)
    
    # State-specific (some states have different deposit amounts)
    state_code = Column(String, nullable=True)  # CA, OR, NY, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BottleReturn(Base):
    """Track bottle/can returns for deposit refunds"""
    __tablename__ = "bottle_returns"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer (optional)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    # Return details
    container_type = Column(String, nullable=False)  # glass, aluminum, plastic
    quantity = Column(Integer, nullable=False)
    deposit_per_unit = Column(Float, nullable=False)
    total_refund = Column(Float, nullable=False)
    
    # Refund method
    refund_method = Column(String, default="cash")  # cash, store_credit, check
    
    # Shift tracking
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    
    # Status
    processed = Column(Boolean, default=True)
    
    # Notes
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProductDeposit(Base):
    """Link products to their deposit requirements"""
    __tablename__ = "product_deposits"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    container_type = Column(String, nullable=False)  # glass, aluminum, plastic
    containers_per_unit = Column(Integer, default=1)  # For 6-packs, 12-packs, etc.
    deposit_per_container = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
