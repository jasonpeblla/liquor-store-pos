# System Health Router - FR-039
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
import os
import platform

from app.database import get_db
from app.models import Sale, Product, Customer, Category

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/health/detailed")
def detailed_health(db: Session = Depends(get_db)):
    """Detailed system health check"""
    # Database check
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Counts
    product_count = db.query(func.count(Product.id)).scalar() or 0
    customer_count = db.query(func.count(Customer.id)).scalar() or 0
    
    # Recent sales (last hour)
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_sales = db.query(func.count(Sale.id)).filter(
        Sale.created_at >= hour_ago
    ).scalar() or 0
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "counts": {
            "products": product_count,
            "customers": customer_count,
            "sales_last_hour": recent_sales
        },
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version()
        }
    }


@router.get("/stats")
def system_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Today's metrics
    today_sales = db.query(func.count(Sale.id)).filter(
        Sale.created_at >= today_start
    ).scalar() or 0
    
    today_revenue = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= today_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    # Total products
    total_products = db.query(func.count(Product.id)).scalar() or 0
    active_categories = db.query(func.count(Category.id)).scalar() or 0
    
    # Inventory value
    inventory_value = db.query(func.sum(Product.price * Product.stock_quantity)).scalar() or 0
    
    return {
        "today": {
            "sales_count": today_sales,
            "revenue": float(today_revenue)
        },
        "inventory": {
            "total_products": total_products,
            "categories": active_categories,
            "total_value": float(inventory_value)
        },
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/database/tables")
def database_info(db: Session = Depends(get_db)):
    """Get database table information"""
    # Get table counts
    tables = {
        "sales": db.query(func.count(Sale.id)).scalar() or 0,
        "products": db.query(func.count(Product.id)).scalar() or 0,
        "customers": db.query(func.count(Customer.id)).scalar() or 0,
        "categories": db.query(func.count(Category.id)).scalar() or 0
    }
    
    return {
        "tables": tables,
        "total_records": sum(tables.values())
    }


@router.get("/uptime")
def get_uptime():
    """Get system uptime info"""
    # This is a simple implementation - in production, track actual start time
    return {
        "status": "running",
        "current_time": datetime.utcnow().isoformat(),
        "timezone": "UTC"
    }


@router.post("/maintenance/cleanup")
def cleanup_old_data(days_old: int = 365, dry_run: bool = True, db: Session = Depends(get_db)):
    """Clean up old audit logs and session data"""
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    
    # For safety, just report what would be cleaned
    # In production, implement actual cleanup with proper authorization
    
    from app.models.audit_log import AuditLog, LoginAttempt
    
    old_audit_logs = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at < cutoff
    ).scalar() or 0
    
    old_login_attempts = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.created_at < cutoff
    ).scalar() or 0
    
    result = {
        "cutoff_date": cutoff.isoformat(),
        "would_delete": {
            "audit_logs": old_audit_logs,
            "login_attempts": old_login_attempts
        },
        "dry_run": dry_run
    }
    
    if not dry_run:
        # Actually delete
        db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete()
        db.query(LoginAttempt).filter(LoginAttempt.created_at < cutoff).delete()
        db.commit()
        result["deleted"] = True
    
    return result


@router.get("/endpoints")
def list_endpoints():
    """List all available API endpoints"""
    return {
        "core": [
            "/products", "/categories", "/sales", "/customers"
        ],
        "inventory": [
            "/inventory", "/inventory-alerts", "/purchase-orders"
        ],
        "compliance": [
            "/compliance", "/age-verification", "/quantity-limits"
        ],
        "pricing": [
            "/promotions", "/happy-hour", "/mix-match", "/price-rules"
        ],
        "customer": [
            "/loyalty", "/reservations", "/gift-cards"
        ],
        "operations": [
            "/shifts", "/employees", "/cash-drawer", "/delivery"
        ],
        "reports": [
            "/reports", "/dashboard"
        ],
        "system": [
            "/system/health", "/system/stats", "/audit"
        ]
    }
