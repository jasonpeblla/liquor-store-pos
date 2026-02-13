from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.models import Sale, SaleItem, Product, Category

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def get_daily_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get sales report for a specific day"""
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.utcnow()
    
    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    
    sales = db.query(Sale).filter(
        Sale.created_at >= start,
        Sale.created_at < end,
        Sale.payment_status == "completed"
    ).all()
    
    total_revenue = sum(s.total for s in sales)
    total_tax = sum(s.tax_amount for s in sales)
    total_items = sum(len(s.items) for s in sales)
    
    # Payment method breakdown
    payment_methods = {}
    for sale in sales:
        method = sale.payment_method
        if method not in payment_methods:
            payment_methods[method] = {"count": 0, "total": 0}
        payment_methods[method]["count"] += 1
        payment_methods[method]["total"] += sale.total
    
    return {
        "date": start.strftime("%Y-%m-%d"),
        "total_sales": len(sales),
        "total_revenue": round(total_revenue, 2),
        "total_tax_collected": round(total_tax, 2),
        "total_items_sold": total_items,
        "average_sale": round(total_revenue / len(sales), 2) if sales else 0,
        "payment_breakdown": payment_methods
    }


@router.get("/weekly")
def get_weekly_report(db: Session = Depends(get_db)):
    """Get sales report for the last 7 days"""
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    
    daily_stats = []
    for i in range(7):
        day_start = (start + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        sales = db.query(Sale).filter(
            Sale.created_at >= day_start,
            Sale.created_at < day_end,
            Sale.payment_status == "completed"
        ).all()
        
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "day": day_start.strftime("%A"),
            "sales_count": len(sales),
            "revenue": round(sum(s.total for s in sales), 2)
        })
    
    total_revenue = sum(d["revenue"] for d in daily_stats)
    total_sales = sum(d["sales_count"] for d in daily_stats)
    
    return {
        "period": f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}",
        "total_revenue": round(total_revenue, 2),
        "total_sales": total_sales,
        "average_daily_revenue": round(total_revenue / 7, 2),
        "daily_breakdown": daily_stats
    }


@router.get("/top-products")
def get_top_products(
    limit: int = 10,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get top selling products"""
    start = datetime.utcnow() - timedelta(days=days)
    
    # Query top products by quantity sold
    results = db.query(
        Product.id,
        Product.name,
        Product.brand,
        func.sum(SaleItem.quantity).label("total_quantity"),
        func.sum(SaleItem.line_total).label("total_revenue")
    ).join(
        SaleItem, SaleItem.product_id == Product.id
    ).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(
        Sale.created_at >= start,
        Sale.payment_status == "completed"
    ).group_by(
        Product.id
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(limit).all()
    
    return {
        "period_days": days,
        "products": [
            {
                "id": r.id,
                "name": r.name,
                "brand": r.brand,
                "total_quantity_sold": r.total_quantity,
                "total_revenue": round(r.total_revenue, 2)
            }
            for r in results
        ]
    }


@router.get("/category-breakdown")
def get_category_breakdown(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get sales breakdown by category"""
    start = datetime.utcnow() - timedelta(days=days)
    
    categories = db.query(Category).all()
    breakdown = []
    
    for category in categories:
        results = db.query(
            func.sum(SaleItem.quantity).label("quantity"),
            func.sum(SaleItem.line_total).label("revenue")
        ).join(
            Product, Product.id == SaleItem.product_id
        ).join(
            Sale, Sale.id == SaleItem.sale_id
        ).filter(
            Product.category_id == category.id,
            Sale.created_at >= start,
            Sale.payment_status == "completed"
        ).first()
        
        breakdown.append({
            "category_id": category.id,
            "category_name": category.name,
            "quantity_sold": results.quantity or 0,
            "revenue": round(results.revenue or 0, 2)
        })
    
    # Sort by revenue descending
    breakdown.sort(key=lambda x: x["revenue"], reverse=True)
    
    return {
        "period_days": days,
        "categories": breakdown,
        "total_revenue": sum(c["revenue"] for c in breakdown)
    }


@router.get("/hourly")
def get_hourly_breakdown(
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get hourly sales breakdown for a day"""
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.utcnow()
    
    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    hourly_data = []
    for hour in range(24):
        hour_start = start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)
        
        sales = db.query(Sale).filter(
            Sale.created_at >= hour_start,
            Sale.created_at < hour_end,
            Sale.payment_status == "completed"
        ).all()
        
        hourly_data.append({
            "hour": hour,
            "time_range": f"{hour:02d}:00 - {(hour+1) % 24:02d}:00",
            "sales_count": len(sales),
            "revenue": round(sum(s.total for s in sales), 2)
        })
    
    peak_hour = max(hourly_data, key=lambda x: x["revenue"])
    
    return {
        "date": start.strftime("%Y-%m-%d"),
        "hourly_breakdown": hourly_data,
        "peak_hour": peak_hour
    }
