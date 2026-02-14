from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from io import StringIO
import csv

from app.database import get_db
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product import Product
from app.models.category import Category
from app.models.age_verification import AgeVerification
from app.models.customer import Customer

router = APIRouter(prefix="/compliance", tags=["compliance"])


# Schemas
class ComplianceReportRequest(BaseModel):
    start_date: date
    end_date: date
    state_code: str = "CA"


class AlcoholSalesSummary(BaseModel):
    category: str
    total_units: int
    total_revenue: float
    total_tax: float
    abv_average: Optional[float]


class ComplianceReport(BaseModel):
    report_period: str
    state_code: str
    generated_at: datetime
    
    # Sales totals
    total_alcohol_sales: float
    total_alcohol_tax: float
    total_non_alcohol_sales: float
    
    # By category
    sales_by_category: List[AlcoholSalesSummary]
    
    # Age verification stats
    total_verifications: int
    declined_verifications: int
    underage_attempts: int
    
    # Compliance metrics
    verification_rate: float  # % of alcohol sales with verification
    
    # Notes/warnings
    warnings: List[str]


@router.post("/generate-report", response_model=ComplianceReport)
def generate_compliance_report(
    request: ComplianceReportRequest,
    db: Session = Depends(get_db)
):
    """Generate state compliance report for alcohol sales"""
    start_dt = datetime.combine(request.start_date, datetime.min.time())
    end_dt = datetime.combine(request.end_date, datetime.max.time())
    
    # Get all sales in period
    sales = db.query(Sale).filter(
        Sale.created_at >= start_dt,
        Sale.created_at <= end_dt,
        Sale.payment_status != "refunded"
    ).all()
    
    sale_ids = [s.id for s in sales]
    
    # Get sale items with product info
    items = db.query(SaleItem, Product, Category).join(
        Product, SaleItem.product_id == Product.id
    ).join(
        Category, Product.category_id == Category.id
    ).filter(
        SaleItem.sale_id.in_(sale_ids)
    ).all()
    
    # Separate alcohol and non-alcohol
    alcohol_categories = ["Beer", "Wine", "Spirits"]
    alcohol_sales = 0.0
    alcohol_tax = 0.0
    non_alcohol_sales = 0.0
    
    category_totals = {}
    alcohol_sale_ids = set()
    
    for item, product, category in items:
        item_total = item.quantity * item.unit_price
        
        if category.name in alcohol_categories:
            alcohol_sales += item_total
            alcohol_tax += item_total * category.tax_rate
            alcohol_sale_ids.add(item.sale_id)
            
            if category.name not in category_totals:
                category_totals[category.name] = {
                    "units": 0,
                    "revenue": 0,
                    "tax": 0,
                    "abv_sum": 0,
                    "abv_count": 0
                }
            
            category_totals[category.name]["units"] += item.quantity
            category_totals[category.name]["revenue"] += item_total
            category_totals[category.name]["tax"] += item_total * category.tax_rate
            
            if product.abv:
                category_totals[category.name]["abv_sum"] += product.abv * item.quantity
                category_totals[category.name]["abv_count"] += item.quantity
        else:
            non_alcohol_sales += item_total
    
    # Get age verifications
    verifications = db.query(AgeVerification).filter(
        AgeVerification.verified_at >= start_dt,
        AgeVerification.verified_at <= end_dt
    ).all()
    
    total_verifications = len(verifications)
    declined = sum(1 for v in verifications if not v.verification_passed)
    underage = sum(1 for v in verifications if v.calculated_age and v.calculated_age < 21)
    
    # Calculate verification rate
    verification_rate = 0.0
    if alcohol_sale_ids:
        verified_sale_ids = set(v.sale_id for v in verifications if v.sale_id and v.verification_passed)
        verification_rate = len(verified_sale_ids.intersection(alcohol_sale_ids)) / len(alcohol_sale_ids) * 100
    
    # Generate warnings
    warnings = []
    if verification_rate < 100:
        warnings.append(f"Verification rate below 100%: {verification_rate:.1f}% of alcohol sales have verified age")
    if declined > 0:
        warnings.append(f"{declined} sales were declined due to failed age verification")
    if underage > 0:
        warnings.append(f"{underage} attempted purchases by underage customers")
    
    # Build category summaries
    sales_by_category = []
    for cat_name, totals in category_totals.items():
        avg_abv = None
        if totals["abv_count"] > 0:
            avg_abv = round(totals["abv_sum"] / totals["abv_count"], 1)
        
        sales_by_category.append(AlcoholSalesSummary(
            category=cat_name,
            total_units=totals["units"],
            total_revenue=round(totals["revenue"], 2),
            total_tax=round(totals["tax"], 2),
            abv_average=avg_abv
        ))
    
    return ComplianceReport(
        report_period=f"{request.start_date} to {request.end_date}",
        state_code=request.state_code,
        generated_at=datetime.utcnow(),
        total_alcohol_sales=round(alcohol_sales, 2),
        total_alcohol_tax=round(alcohol_tax, 2),
        total_non_alcohol_sales=round(non_alcohol_sales, 2),
        sales_by_category=sales_by_category,
        total_verifications=total_verifications,
        declined_verifications=declined,
        underage_attempts=underage,
        verification_rate=round(verification_rate, 1),
        warnings=warnings
    )


@router.get("/age-verification-log")
def age_verification_log(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    failed_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get age verification audit log"""
    query = db.query(AgeVerification)
    
    if start_date:
        query = query.filter(AgeVerification.verified_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(AgeVerification.verified_at <= datetime.combine(end_date, datetime.max.time()))
    if failed_only:
        query = query.filter(AgeVerification.verification_passed == False)
    
    verifications = query.order_by(AgeVerification.verified_at.desc()).all()
    
    return [
        {
            "id": v.id,
            "sale_id": v.sale_id,
            "customer_id": v.customer_id,
            "verification_method": v.verification_method,
            "dob": v.date_of_birth,
            "calculated_age": v.calculated_age,
            "passed": v.verification_passed,
            "verified_at": v.verified_at,
            "employee_id": v.verified_by
        }
        for v in verifications
    ]


@router.get("/export/alcohol-sales-csv")
def export_alcohol_sales_csv(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Export alcohol sales data as CSV for state reporting"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # Get sale items with joins
    items = db.query(
        Sale, SaleItem, Product, Category
    ).join(
        SaleItem, Sale.id == SaleItem.sale_id
    ).join(
        Product, SaleItem.product_id == Product.id
    ).join(
        Category, Product.category_id == Category.id
    ).filter(
        Sale.created_at >= start_dt,
        Sale.created_at <= end_dt,
        Sale.payment_status != "refunded",
        Category.name.in_(["Beer", "Wine", "Spirits"])
    ).all()
    
    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Sale Date", "Sale ID", "Product Name", "Brand", "Category",
        "ABV %", "Size", "Quantity", "Unit Price", "Total", "Tax Rate", "Tax Amount"
    ])
    
    for sale, item, product, category in items:
        item_total = item.quantity * item.unit_price
        tax_amount = item_total * category.tax_rate
        
        writer.writerow([
            sale.created_at.strftime("%Y-%m-%d %H:%M"),
            sale.id,
            product.name,
            product.brand or "",
            category.name,
            product.abv or "",
            product.size or "",
            item.quantity,
            f"{item.unit_price:.2f}",
            f"{item_total:.2f}",
            f"{category.tax_rate * 100:.1f}%",
            f"{tax_amount:.2f}"
        ])
    
    return {
        "filename": f"alcohol_sales_{start_date}_to_{end_date}.csv",
        "content": output.getvalue(),
        "row_count": len(items)
    }


@router.get("/daily-summary")
def daily_compliance_summary(
    report_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Quick daily compliance summary"""
    if not report_date:
        report_date = date.today()
    
    start_dt = datetime.combine(report_date, datetime.min.time())
    end_dt = datetime.combine(report_date, datetime.max.time())
    
    # Count sales
    total_sales = db.query(Sale).filter(
        Sale.created_at >= start_dt,
        Sale.created_at <= end_dt,
        Sale.payment_status != "refunded"
    ).count()
    
    # Count verifications
    verifications = db.query(AgeVerification).filter(
        AgeVerification.verified_at >= start_dt,
        AgeVerification.verified_at <= end_dt
    ).all()
    
    passed = sum(1 for v in verifications if v.verification_passed)
    failed = sum(1 for v in verifications if not v.verification_passed)
    
    return {
        "date": report_date,
        "total_sales": total_sales,
        "age_verifications": len(verifications),
        "verifications_passed": passed,
        "verifications_failed": failed,
        "compliance_status": "OK" if failed == 0 else "REVIEW REQUIRED"
    }


@router.get("/quantity-limits")
def get_quantity_limits():
    """Get configured purchase quantity limits (state-specific)"""
    # These would typically come from a config or database
    # Different states have different limits
    return {
        "state": "CA",
        "limits": {
            "spirits": {
                "per_transaction": 6,  # bottles
                "per_day_per_customer": 12,
                "requires_id_above": 2
            },
            "wine": {
                "per_transaction": 12,
                "per_day_per_customer": 36,
                "requires_id_above": 3
            },
            "beer": {
                "per_transaction": None,  # No limit
                "per_day_per_customer": None,
                "requires_id_above": 5  # cases
            }
        },
        "notes": [
            "ID required for all alcohol purchases",
            "Large quantity purchases may require manager approval",
            "Resale to minors is a criminal offense"
        ]
    }


@router.post("/check-customer-limits")
def check_customer_limits(
    customer_id: int,
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):
    """Check if a purchase would exceed customer limits"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    category = db.query(Category).filter(Category.id == product.category_id).first()
    
    # Get today's purchases by this customer
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    today_purchases = db.query(func.sum(SaleItem.quantity)).join(
        Sale, SaleItem.sale_id == Sale.id
    ).filter(
        Sale.customer_id == customer_id,
        Sale.created_at >= today_start,
        Sale.payment_status != "refunded",
        SaleItem.product_id == product_id
    ).scalar() or 0
    
    # Check against limits (simplified)
    limits = get_quantity_limits()
    cat_limits = limits["limits"].get(category.name.lower(), {})
    daily_limit = cat_limits.get("per_day_per_customer")
    
    would_exceed = False
    message = "OK"
    
    if daily_limit and (today_purchases + quantity) > daily_limit:
        would_exceed = True
        message = f"Would exceed daily limit of {daily_limit} for {category.name}"
    
    return {
        "customer_id": customer_id,
        "product_id": product_id,
        "category": category.name,
        "requested_quantity": quantity,
        "already_purchased_today": today_purchases,
        "daily_limit": daily_limit,
        "would_exceed_limit": would_exceed,
        "message": message
    }
