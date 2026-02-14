from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from datetime import datetime
from app.database import Base
import hashlib


class Employee(Base):
    """Employee accounts with PIN-based authentication"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    employee_number = Column(String, unique=True, index=True)  # E001, E002, etc.
    
    # Authentication
    pin_hash = Column(String, nullable=False)  # Hashed 4-6 digit PIN
    
    # Contact
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    # Role and permissions
    role = Column(String, default="cashier")  # cashier, supervisor, manager, admin
    permissions = Column(JSON, nullable=True)  # Override specific permissions
    
    # Pay info (optional)
    hourly_rate = Column(Float, nullable=True)
    
    # Training/compliance
    alcohol_certified = Column(Boolean, default=False)
    certification_expiry = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    hire_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Default role permissions
ROLE_PERMISSIONS = {
    "cashier": {
        "can_process_sales": True,
        "can_void_items": False,
        "can_void_transactions": False,
        "can_apply_discounts": False,
        "can_process_returns": False,
        "can_open_drawer": False,
        "can_view_reports": False,
        "can_manage_inventory": False,
        "can_manage_employees": False,
        "can_manage_settings": False,
        "discount_limit": 0,
    },
    "supervisor": {
        "can_process_sales": True,
        "can_void_items": True,
        "can_void_transactions": True,
        "can_apply_discounts": True,
        "can_process_returns": True,
        "can_open_drawer": True,
        "can_view_reports": False,
        "can_manage_inventory": False,
        "can_manage_employees": False,
        "can_manage_settings": False,
        "discount_limit": 10,  # Max 10% discount
    },
    "manager": {
        "can_process_sales": True,
        "can_void_items": True,
        "can_void_transactions": True,
        "can_apply_discounts": True,
        "can_process_returns": True,
        "can_open_drawer": True,
        "can_view_reports": True,
        "can_manage_inventory": True,
        "can_manage_employees": False,
        "can_manage_settings": False,
        "discount_limit": 25,
    },
    "admin": {
        "can_process_sales": True,
        "can_void_items": True,
        "can_void_transactions": True,
        "can_apply_discounts": True,
        "can_process_returns": True,
        "can_open_drawer": True,
        "can_view_reports": True,
        "can_manage_inventory": True,
        "can_manage_employees": True,
        "can_manage_settings": True,
        "discount_limit": 100,
    },
}


def hash_pin(pin: str) -> str:
    """Hash a PIN for storage"""
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Verify a PIN against its hash"""
    return hash_pin(pin) == pin_hash
