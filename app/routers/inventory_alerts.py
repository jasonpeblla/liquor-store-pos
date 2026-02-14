# Inventory Alerts Router - FR-031
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.inventory_alert import InventoryAlert, AlertRule, InventorySnapshot
from app.models import Product, Category

router = APIRouter(prefix="/inventory-alerts", tags=["inventory-alerts"])


class AlertRuleCreate(BaseModel):
    name: str
    alert_type: str
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    threshold: float
    comparison: str = "less_than"
    severity: str = "warning"
    notify_email: Optional[str] = None


@router.get("/")
def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List inventory alerts"""
    query = db.query(InventoryAlert)
    
    if status:
        query = query.filter(InventoryAlert.status == status)
    if severity:
        query = query.filter(InventoryAlert.severity == severity)
    if alert_type:
        query = query.filter(InventoryAlert.alert_type == alert_type)
    
    return query.order_by(desc(InventoryAlert.created_at)).limit(limit).all()


@router.get("/active")
def get_active_alerts(db: Session = Depends(get_db)):
    """Get all active alerts grouped by severity"""
    critical = db.query(InventoryAlert).filter(
        InventoryAlert.status == "active",
        InventoryAlert.severity == "critical"
    ).all()
    
    warnings = db.query(InventoryAlert).filter(
        InventoryAlert.status == "active",
        InventoryAlert.severity == "warning"
    ).all()
    
    info = db.query(InventoryAlert).filter(
        InventoryAlert.status == "active",
        InventoryAlert.severity == "info"
    ).all()
    
    return {
        "critical": critical,
        "warning": warnings,
        "info": info,
        "total_active": len(critical) + len(warnings) + len(info)
    }


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, employee_id: int, db: Session = Depends(get_db)):
    """Acknowledge an alert"""
    alert = db.query(InventoryAlert).filter(InventoryAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "acknowledged"
    alert.acknowledged_by = employee_id
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Alert acknowledged"}


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark alert as resolved"""
    alert = db.query(InventoryAlert).filter(InventoryAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Alert resolved"}


@router.post("/scan")
def scan_inventory_alerts(db: Session = Depends(get_db)):
    """Scan inventory and generate alerts"""
    alerts_generated = []
    
    # Check low stock
    low_stock = db.query(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.stock_quantity > 0
    ).all()
    
    for product in low_stock:
        existing = db.query(InventoryAlert).filter(
            InventoryAlert.product_id == product.id,
            InventoryAlert.alert_type == "low_stock",
            InventoryAlert.status == "active"
        ).first()
        
        if not existing:
            alert = InventoryAlert(
                alert_type="low_stock",
                severity="warning",
                product_id=product.id,
                message=f"Low stock alert: {product.name}",
                details=f"Current: {product.stock_quantity}, Threshold: {product.low_stock_threshold}",
                threshold_value=product.low_stock_threshold,
                current_value=product.stock_quantity
            )
            db.add(alert)
            alerts_generated.append(product.name)
    
    # Check out of stock
    out_of_stock = db.query(Product).filter(Product.stock_quantity == 0).all()
    
    for product in out_of_stock:
        existing = db.query(InventoryAlert).filter(
            InventoryAlert.product_id == product.id,
            InventoryAlert.alert_type == "out_of_stock",
            InventoryAlert.status == "active"
        ).first()
        
        if not existing:
            alert = InventoryAlert(
                alert_type="out_of_stock",
                severity="critical",
                product_id=product.id,
                message=f"Out of stock: {product.name}",
                current_value=0
            )
            db.add(alert)
            alerts_generated.append(f"{product.name} (OUT)")
    
    db.commit()
    
    return {
        "alerts_generated": len(alerts_generated),
        "products": alerts_generated
    }


# Alert Rules
@router.post("/rules")
def create_alert_rule(rule: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create custom alert rule"""
    db_rule = AlertRule(**rule.dict(), is_active=True)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/rules")
def list_alert_rules(db: Session = Depends(get_db)):
    """List alert rules"""
    return db.query(AlertRule).filter(AlertRule.is_active == True).all()


# Snapshots
@router.post("/snapshot")
def create_inventory_snapshot(db: Session = Depends(get_db)):
    """Create daily inventory snapshot"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    products = db.query(Product).all()
    snapshots_created = 0
    
    for product in products:
        existing = db.query(InventorySnapshot).filter(
            InventorySnapshot.product_id == product.id,
            InventorySnapshot.snapshot_date >= today_start
        ).first()
        
        if not existing:
            snapshot = InventorySnapshot(
                snapshot_date=datetime.utcnow(),
                product_id=product.id,
                quantity=product.stock_quantity,
                value=product.stock_quantity * product.price
            )
            db.add(snapshot)
            snapshots_created += 1
    
    db.commit()
    return {"snapshots_created": snapshots_created}


@router.get("/trends/{product_id}")
def get_inventory_trends(product_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get inventory trends for a product"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    snapshots = db.query(InventorySnapshot).filter(
        InventorySnapshot.product_id == product_id,
        InventorySnapshot.snapshot_date >= start_date
    ).order_by(InventorySnapshot.snapshot_date).all()
    
    return {
        "product_id": product_id,
        "days": days,
        "data": [
            {
                "date": s.snapshot_date.isoformat(),
                "quantity": s.quantity,
                "value": s.value
            }
            for s in snapshots
        ]
    }
