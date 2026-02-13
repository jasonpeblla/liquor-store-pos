from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Promotion, Product, Category

router = APIRouter(prefix="/promotions", tags=["promotions"])


class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    promo_type: str = "percentage"  # percentage, fixed_amount, buy_x_get_y
    discount_value: float
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    scope: str = "all"  # all, category, product
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    min_purchase: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_uses: Optional[int] = None


@router.get("")
def list_promotions(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all promotions"""
    query = db.query(Promotion)
    
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            Promotion.is_active == True,
            Promotion.start_date <= now,
            ((Promotion.end_date == None) | (Promotion.end_date >= now))
        )
    
    promotions = query.all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "promo_type": p.promo_type,
            "discount_value": p.discount_value,
            "scope": p.scope,
            "min_purchase": p.min_purchase,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "is_active": p.is_active,
            "uses_remaining": (p.max_uses - p.current_uses) if p.max_uses else None
        }
        for p in promotions
    ]


@router.post("")
def create_promotion(promo: PromotionCreate, db: Session = Depends(get_db)):
    """Create a new promotion"""
    # Validate scope
    if promo.scope == "category" and not promo.category_id:
        raise HTTPException(status_code=400, detail="Category ID required for category scope")
    if promo.scope == "product" and not promo.product_id:
        raise HTTPException(status_code=400, detail="Product ID required for product scope")
    
    # Validate buy X get Y
    if promo.promo_type == "buy_x_get_y":
        if not promo.buy_quantity or not promo.get_quantity:
            raise HTTPException(status_code=400, detail="Buy and get quantities required for BOGO deals")
    
    db_promo = Promotion(
        **promo.model_dump(),
        start_date=promo.start_date or datetime.utcnow()
    )
    db.add(db_promo)
    db.commit()
    db.refresh(db_promo)
    
    return {"id": db_promo.id, "name": db_promo.name, "created": True}


@router.get("/{promo_id}")
def get_promotion(promo_id: int, db: Session = Depends(get_db)):
    """Get promotion details"""
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promo


@router.delete("/{promo_id}")
def deactivate_promotion(promo_id: int, db: Session = Depends(get_db)):
    """Deactivate a promotion"""
    promo = db.query(Promotion).filter(Promotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    promo.is_active = False
    db.commit()
    return {"message": "Promotion deactivated"}


@router.post("/calculate")
def calculate_discounts(
    items: List[dict],
    db: Session = Depends(get_db)
):
    """Calculate applicable discounts for cart items
    
    Input: [{"product_id": 1, "quantity": 2, "unit_price": 10.00}, ...]
    """
    now = datetime.utcnow()
    
    # Get active promotions
    promotions = db.query(Promotion).filter(
        Promotion.is_active == True,
        Promotion.start_date <= now,
        ((Promotion.end_date == None) | (Promotion.end_date >= now))
    ).all()
    
    total_discount = 0.0
    applied_promos = []
    subtotal = sum(item["unit_price"] * item["quantity"] for item in items)
    
    for promo in promotions:
        # Check minimum purchase
        if subtotal < promo.min_purchase:
            continue
        
        # Check usage limits
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            continue
        
        discount = 0.0
        
        if promo.scope == "all":
            # Apply to entire cart
            if promo.promo_type == "percentage":
                discount = subtotal * (promo.discount_value / 100)
            elif promo.promo_type == "fixed_amount":
                discount = min(promo.discount_value, subtotal)
        
        elif promo.scope == "category":
            # Apply to items in category
            for item in items:
                product = db.query(Product).filter(Product.id == item["product_id"]).first()
                if product and product.category_id == promo.category_id:
                    item_total = item["unit_price"] * item["quantity"]
                    if promo.promo_type == "percentage":
                        discount += item_total * (promo.discount_value / 100)
                    elif promo.promo_type == "fixed_amount":
                        discount += min(promo.discount_value, item_total)
        
        elif promo.scope == "product":
            # Apply to specific product
            for item in items:
                if item["product_id"] == promo.product_id:
                    item_total = item["unit_price"] * item["quantity"]
                    if promo.promo_type == "percentage":
                        discount += item_total * (promo.discount_value / 100)
                    elif promo.promo_type == "fixed_amount":
                        discount += min(promo.discount_value, item_total)
        
        if discount > 0:
            total_discount += discount
            applied_promos.append({
                "promo_id": promo.id,
                "name": promo.name,
                "discount": round(discount, 2)
            })
    
    return {
        "subtotal": round(subtotal, 2),
        "total_discount": round(total_discount, 2),
        "final_subtotal": round(subtotal - total_discount, 2),
        "applied_promotions": applied_promos
    }
