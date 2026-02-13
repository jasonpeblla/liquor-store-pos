from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import Sale, SaleItem, Product, Customer, Category
from app.schemas import SaleCreate, SaleResponse

router = APIRouter(prefix="/sales", tags=["sales"])

# Default sales tax rate
BASE_TAX_RATE = 0.0875  # 8.75% base sales tax


def calculate_sale_totals(items: List[SaleItem], db: Session) -> dict:
    """Calculate subtotal, tax, and total for a sale"""
    subtotal = 0.0
    tax_amount = 0.0
    discount_amount = 0.0
    
    for item in items:
        subtotal += item.line_total
        
        # Get product's category tax rate
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product and product.category:
            category_tax = product.category.tax_rate
            item_tax = item.line_total * (BASE_TAX_RATE + category_tax)
            tax_amount += item_tax
        else:
            tax_amount += item.line_total * BASE_TAX_RATE
    
    return {
        "subtotal": round(subtotal, 2),
        "tax_amount": round(tax_amount, 2),
        "discount_amount": round(discount_amount, 2),
        "total": round(subtotal + tax_amount - discount_amount, 2)
    }


def sale_to_response(sale: Sale) -> dict:
    """Convert sale model to response"""
    customer_name = None
    if sale.customer:
        customer_name = sale.customer.name
    
    items = []
    for item in sale.items:
        product_name = None
        if item.product:
            product_name = item.product.name
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "is_case_price": item.is_case_price,
            "discount_applied": item.discount_applied,
            "line_total": item.line_total
        })
    
    return {
        "id": sale.id,
        "customer_id": sale.customer_id,
        "customer_name": customer_name,
        "subtotal": sale.subtotal,
        "tax_amount": sale.tax_amount,
        "discount_amount": sale.discount_amount,
        "total": sale.total,
        "payment_method": sale.payment_method,
        "payment_status": sale.payment_status,
        "age_verified": sale.age_verified,
        "items": items,
        "created_at": sale.created_at
    }


@router.get("", response_model=List[SaleResponse])
def list_sales(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent sales"""
    sales = db.query(Sale).order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()
    return [sale_to_response(s) for s in sales]


@router.post("", response_model=SaleResponse)
def create_sale(sale_data: SaleCreate, db: Session = Depends(get_db)):
    """Create a new sale"""
    # Check if any product requires age verification
    requires_age_check = False
    for item in sale_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        if product.requires_age_verification:
            requires_age_check = True
    
    # Verify age if required
    if requires_age_check and not sale_data.age_verified:
        raise HTTPException(
            status_code=400, 
            detail="Age verification required for alcohol purchase"
        )
    
    # Create sale
    db_sale = Sale(
        customer_id=sale_data.customer_id,
        payment_method=sale_data.payment_method,
        age_verified=sale_data.age_verified,
        age_verified_at=datetime.utcnow() if sale_data.age_verified else None
    )
    db.add(db_sale)
    db.flush()  # Get the sale ID
    
    # Add items
    sale_items = []
    for item_data in sale_data.items:
        product = db.query(Product).filter(Product.id == item_data.product_id).first()
        
        # Check stock
        if product.stock_quantity < item_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}"
            )
        
        # Calculate pricing (check for case discount)
        is_case_price = False
        unit_price = product.price
        
        if product.case_price and item_data.quantity >= product.case_size:
            # Apply case pricing
            full_cases = item_data.quantity // product.case_size
            remaining = item_data.quantity % product.case_size
            
            case_total = full_cases * product.case_price
            remaining_total = remaining * product.price
            line_total = case_total + remaining_total
            is_case_price = True
            unit_price = line_total / item_data.quantity  # Average price per unit
        else:
            line_total = unit_price * item_data.quantity
        
        sale_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            is_case_price=is_case_price,
            line_total=round(line_total, 2)
        )
        db.add(sale_item)
        sale_items.append(sale_item)
        
        # Update inventory
        product.stock_quantity -= item_data.quantity
        product.times_sold += item_data.quantity
    
    db.flush()
    
    # Calculate totals
    totals = calculate_sale_totals(sale_items, db)
    db_sale.subtotal = totals["subtotal"]
    db_sale.tax_amount = totals["tax_amount"]
    db_sale.discount_amount = totals["discount_amount"]
    db_sale.total = totals["total"]
    db_sale.payment_status = "completed"
    
    # Update customer stats
    if db_sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == db_sale.customer_id).first()
        if customer:
            customer.total_spent += db_sale.total
            customer.loyalty_points += int(db_sale.total)  # 1 point per dollar
    
    db.commit()
    db.refresh(db_sale)
    
    return sale_to_response(db_sale)


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    """Get a specific sale"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale_to_response(sale)


@router.post("/{sale_id}/refund")
def refund_sale(sale_id: int, db: Session = Depends(get_db)):
    """Refund a sale"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if sale.payment_status == "refunded":
        raise HTTPException(status_code=400, detail="Sale already refunded")
    
    # Restore inventory
    for item in sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock_quantity += item.quantity
            product.times_sold -= item.quantity
    
    # Update customer stats
    if sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
        if customer:
            customer.total_spent -= sale.total
            customer.loyalty_points -= int(sale.total)
    
    sale.payment_status = "refunded"
    db.commit()
    
    return {"message": "Sale refunded", "sale_id": sale_id}
