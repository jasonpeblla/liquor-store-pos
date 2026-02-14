# Dashboard Router - FR-023
# Real-time analytics and KPI dashboard for liquor store management

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.models import Sale, SaleItem, Product, Category, Customer, Shift, AgeVerification

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get key metrics for dashboard display"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Today's sales
    today_sales = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= today_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    today_count = db.query(func.count(Sale.id)).filter(
        Sale.created_at >= today_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    # This week
    week_sales = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= week_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    # This month
    month_sales = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= month_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    # Average transaction
    avg_transaction = db.query(func.avg(Sale.total)).filter(
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    # Items in stock
    total_stock = db.query(func.sum(Product.stock_quantity)).scalar() or 0
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.stock_quantity > 0
    ).scalar() or 0
    out_of_stock = db.query(func.count(Product.id)).filter(
        Product.stock_quantity == 0
    ).scalar() or 0
    
    # Active customers
    active_customers = db.query(func.count(Customer.id)).scalar() or 0
    
    # Age verifications today
    age_verifications = db.query(func.count(AgeVerification.id)).filter(
        AgeVerification.verified_at >= today_start
    ).scalar() or 0
    
    return {
        "today": {
            "sales": float(today_sales),
            "transactions": today_count,
            "average": float(today_sales / today_count) if today_count > 0 else 0
        },
        "week": {
            "sales": float(week_sales)
        },
        "month": {
            "sales": float(month_sales)
        },
        "average_transaction": float(avg_transaction),
        "inventory": {
            "total_units": int(total_stock),
            "low_stock_items": low_stock_count,
            "out_of_stock_items": out_of_stock
        },
        "customers": {
            "total": active_customers
        },
        "compliance": {
            "age_verifications_today": age_verifications
        }
    }


@router.get("/sales-chart")
def get_sales_chart(days: int = 7, db: Session = Depends(get_db)):
    """Get sales data for chart visualization"""
    data = []
    today = datetime.now().date()
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        start = datetime.combine(date, datetime.min.time())
        end = start + timedelta(days=1)
        
        daily_total = db.query(func.sum(Sale.total)).filter(
            Sale.created_at >= start,
            Sale.created_at < end,
            Sale.payment_status == "completed"
        ).scalar() or 0
        
        daily_count = db.query(func.count(Sale.id)).filter(
            Sale.created_at >= start,
            Sale.created_at < end,
            Sale.payment_status == "completed"
        ).scalar() or 0
        
        data.append({
            "date": date.isoformat(),
            "day": date.strftime("%a"),
            "sales": float(daily_total),
            "transactions": daily_count
        })
    
    return {"data": data}


@router.get("/category-breakdown")
def get_category_breakdown(db: Session = Depends(get_db)):
    """Get sales breakdown by category"""
    results = db.query(
        Category.name,
        func.sum(SaleItem.subtotal).label("total"),
        func.sum(SaleItem.quantity).label("units")
    ).join(
        Product, Product.category_id == Category.id
    ).join(
        SaleItem, SaleItem.product_id == Product.id
    ).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(
        Sale.payment_status == "completed"
    ).group_by(Category.name).all()
    
    return {
        "categories": [
            {
                "name": name,
                "sales": float(total or 0),
                "units": int(units or 0)
            }
            for name, total, units in results
        ]
    }


@router.get("/top-products")
def get_top_products(limit: int = 10, db: Session = Depends(get_db)):
    """Get top selling products"""
    results = db.query(
        Product.id,
        Product.name,
        Product.brand,
        func.sum(SaleItem.quantity).label("units_sold"),
        func.sum(SaleItem.subtotal).label("revenue")
    ).join(
        SaleItem, SaleItem.product_id == Product.id
    ).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(
        Sale.payment_status == "completed"
    ).group_by(Product.id).order_by(desc("revenue")).limit(limit).all()
    
    return {
        "products": [
            {
                "id": id,
                "name": name,
                "brand": brand,
                "units_sold": int(units or 0),
                "revenue": float(revenue or 0)
            }
            for id, name, brand, units, revenue in results
        ]
    }


@router.get("/hourly-traffic")
def get_hourly_traffic(db: Session = Depends(get_db)):
    """Get transaction count by hour for today"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    hours = []
    for hour in range(24):
        start = today_start + timedelta(hours=hour)
        end = start + timedelta(hours=1)
        
        count = db.query(func.count(Sale.id)).filter(
            Sale.created_at >= start,
            Sale.created_at < end,
            Sale.payment_status == "completed"
        ).scalar() or 0
        
        hours.append({
            "hour": hour,
            "label": f"{hour:02d}:00",
            "transactions": count
        })
    
    return {"hours": hours}


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    """Get actionable alerts for dashboard"""
    alerts = []
    
    # Low stock alerts
    low_stock = db.query(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.stock_quantity > 0
    ).limit(5).all()
    
    for p in low_stock:
        alerts.append({
            "type": "low_stock",
            "severity": "warning",
            "message": f"{p.name} is low on stock ({p.stock_quantity} remaining)",
            "product_id": p.id
        })
    
    # Out of stock
    out_of_stock = db.query(Product).filter(
        Product.stock_quantity == 0
    ).limit(5).all()
    
    for p in out_of_stock:
        alerts.append({
            "type": "out_of_stock",
            "severity": "critical",
            "message": f"{p.name} is out of stock",
            "product_id": p.id
        })
    
    return {"alerts": alerts}


@router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)):
    """Get key performance indicators"""
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    yesterday_start = today_start - timedelta(days=1)
    
    # Today vs yesterday comparison
    today_sales = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= today_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    yesterday_sales = db.query(func.sum(Sale.total)).filter(
        Sale.created_at >= yesterday_start,
        Sale.created_at < today_start,
        Sale.payment_status == "completed"
    ).scalar() or 0
    
    sales_change = ((today_sales - yesterday_sales) / yesterday_sales * 100) if yesterday_sales > 0 else 0
    
    # Total products
    total_products = db.query(func.count(Product.id)).scalar() or 0
    
    # Total categories
    total_categories = db.query(func.count(Category.id)).scalar() or 0
    
    return {
        "sales_today": float(today_sales),
        "sales_yesterday": float(yesterday_sales),
        "sales_change_percent": round(sales_change, 1),
        "total_products": total_products,
        "total_categories": total_categories
    }
