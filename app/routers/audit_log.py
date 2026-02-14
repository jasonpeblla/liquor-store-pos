# Audit Log Router - FR-038
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.models.audit_log import AuditLog, PriceChangeLog, LoginAttempt

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    user_id: Optional[int] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: str = "no"


class PriceChangeCreate(BaseModel):
    product_id: int
    old_price: float
    new_price: float
    changed_by: Optional[int] = None
    reason: Optional[str] = None


@router.post("/log")
def create_audit_log(log: AuditLogCreate, db: Session = Depends(get_db)):
    """Create an audit log entry"""
    db_log = AuditLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


@router.get("/logs")
def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    is_sensitive: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Query audit logs"""
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if is_sensitive:
        query = query.filter(AuditLog.is_sensitive == is_sensitive)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


@router.get("/logs/entity/{entity_type}/{entity_id}")
def get_entity_history(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """Get audit history for a specific entity"""
    logs = db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    ).order_by(desc(AuditLog.created_at)).all()
    
    return logs


# Price change tracking
@router.post("/price-change")
def log_price_change(change: PriceChangeCreate, db: Session = Depends(get_db)):
    """Log a price change"""
    change_percent = ((change.new_price - change.old_price) / change.old_price) * 100 if change.old_price > 0 else 0
    
    db_change = PriceChangeLog(
        **change.dict(),
        change_percent=round(change_percent, 2)
    )
    db.add(db_change)
    
    # Also create audit log
    audit = AuditLog(
        action="price_change",
        entity_type="product",
        entity_id=change.product_id,
        user_id=change.changed_by,
        old_value=json.dumps({"price": change.old_price}),
        new_value=json.dumps({"price": change.new_price}),
        is_sensitive="moderate"
    )
    db.add(audit)
    
    db.commit()
    db.refresh(db_change)
    return db_change


@router.get("/price-changes")
def get_price_changes(
    product_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get price change history"""
    start_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(PriceChangeLog).filter(PriceChangeLog.created_at >= start_date)
    
    if product_id:
        query = query.filter(PriceChangeLog.product_id == product_id)
    
    return query.order_by(desc(PriceChangeLog.created_at)).all()


# Login tracking
@router.post("/login-attempt")
def log_login(
    employee_id: Optional[int] = None,
    username: Optional[str] = None,
    success: bool = True,
    failure_reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Log a login attempt"""
    attempt = LoginAttempt(
        employee_id=employee_id,
        username=username,
        success="yes" if success else "no",
        failure_reason=failure_reason
    )
    db.add(attempt)
    db.commit()
    return {"logged": True}


@router.get("/login-attempts")
def get_login_attempts(
    employee_id: Optional[int] = None,
    success_only: Optional[bool] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get login attempts"""
    query = db.query(LoginAttempt)
    
    if employee_id:
        query = query.filter(LoginAttempt.employee_id == employee_id)
    if success_only is not None:
        query = query.filter(LoginAttempt.success == ("yes" if success_only else "no"))
    
    return query.order_by(desc(LoginAttempt.created_at)).limit(limit).all()


@router.get("/security-report")
def security_report(db: Session = Depends(get_db)):
    """Get security/audit summary"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Sensitive actions today
    sensitive_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.is_sensitive != "no",
        AuditLog.created_at >= today_start
    ).scalar() or 0
    
    # Failed logins today
    failed_logins = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.success == "no",
        LoginAttempt.created_at >= today_start
    ).scalar() or 0
    
    # Price changes today
    price_changes = db.query(func.count(PriceChangeLog.id)).filter(
        PriceChangeLog.created_at >= today_start
    ).scalar() or 0
    
    return {
        "sensitive_actions_today": sensitive_count,
        "failed_logins_today": failed_logins,
        "price_changes_today": price_changes
    }
