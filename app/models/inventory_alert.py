# Inventory Alerts - FR-031
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class InventoryAlert(Base):
    """Inventory alerts and notifications"""
    __tablename__ = "inventory_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    alert_type = Column(String, nullable=False)  # low_stock, out_of_stock, overstock, expiring, reorder
    severity = Column(String, default="info")  # info, warning, critical
    
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON details
    
    # Status
    status = Column(String, default="active")  # active, acknowledged, resolved, dismissed
    acknowledged_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Threshold that triggered
    threshold_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    """Custom alert rules"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)  # low_stock, velocity_drop, category_threshold
    
    # Conditions
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    threshold = Column(Float, nullable=False)
    comparison = Column(String, default="less_than")  # less_than, greater_than, equals
    
    # Notification
    notify_email = Column(String, nullable=True)
    notify_sms = Column(String, nullable=True)
    severity = Column(String, default="warning")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InventorySnapshot(Base):
    """Daily inventory snapshots for trending"""
    __tablename__ = "inventory_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    
    snapshot_date = Column(DateTime, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)  # quantity * cost
    
    # Velocity metrics
    units_sold_today = Column(Integer, default=0)
    days_of_stock = Column(Float, nullable=True)  # Based on avg daily sales
    
    created_at = Column(DateTime, default=datetime.utcnow)
