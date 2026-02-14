# Price Rules Router - FR-030
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.price_rules import PriceRule, VolumeDiscount, BundlePrice
from app.models import Product

router = APIRouter(prefix="/price-rules", tags=["price-rules"])


class PriceRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    min_quantity: Optional[int] = None
    customer_tier: Optional[str] = None
    discount_type: str = "percent"
    discount_value: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: int = 0
    stackable: bool = False


class VolumeDiscountCreate(BaseModel):
    name: str
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    tiers: List[dict]  # [{"min_qty": 6, "discount_percent": 10}]


class BundleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    product_ids: str  # Comma-separated
    bundle_price: float
    savings_display: Optional[str] = None


@router.post("/rules")
def create_price_rule(rule: PriceRuleCreate, db: Session = Depends(get_db)):
    """Create a dynamic price rule"""
    db_rule = PriceRule(**rule.dict(), is_active=True)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/rules")
def list_price_rules(
    rule_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List price rules"""
    query = db.query(PriceRule)
    if active_only:
        query = query.filter(PriceRule.is_active == True)
    if rule_type:
        query = query.filter(PriceRule.rule_type == rule_type)
    return query.order_by(PriceRule.priority.desc()).all()


@router.post("/volume")
def create_volume_discount(discount: VolumeDiscountCreate, db: Session = Depends(get_db)):
    """Create volume discount tiers"""
    db_discount = VolumeDiscount(
        name=discount.name,
        product_id=discount.product_id,
        category_id=discount.category_id,
        tiers=json.dumps(discount.tiers),
        is_active=True
    )
    db.add(db_discount)
    db.commit()
    db.refresh(db_discount)
    return db_discount


@router.get("/volume")
def list_volume_discounts(db: Session = Depends(get_db)):
    """List volume discounts"""
    discounts = db.query(VolumeDiscount).filter(VolumeDiscount.is_active == True).all()
    result = []
    for d in discounts:
        result.append({
            "id": d.id,
            "name": d.name,
            "product_id": d.product_id,
            "category_id": d.category_id,
            "tiers": json.loads(d.tiers) if d.tiers else []
        })
    return result


@router.post("/bundles")
def create_bundle(bundle: BundleCreate, db: Session = Depends(get_db)):
    """Create a product bundle"""
    db_bundle = BundlePrice(**bundle.dict(), is_active=True)
    db.add(db_bundle)
    db.commit()
    db.refresh(db_bundle)
    return db_bundle


@router.get("/bundles")
def list_bundles(active_only: bool = True, db: Session = Depends(get_db)):
    """List product bundles"""
    query = db.query(BundlePrice)
    if active_only:
        query = query.filter(BundlePrice.is_active == True)
    return query.all()


@router.post("/calculate")
def calculate_price(
    product_id: int,
    quantity: int,
    customer_tier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Calculate final price with all applicable rules"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    base_price = product.price
    final_price = base_price * quantity
    discounts_applied = []
    
    # Check volume discounts
    volume_discounts = db.query(VolumeDiscount).filter(
        VolumeDiscount.is_active == True,
        (VolumeDiscount.product_id == product_id) | (VolumeDiscount.category_id == product.category_id)
    ).all()
    
    for vd in volume_discounts:
        tiers = json.loads(vd.tiers) if vd.tiers else []
        applicable_tier = None
        for tier in sorted(tiers, key=lambda x: x.get("min_qty", 0), reverse=True):
            if quantity >= tier.get("min_qty", 0):
                applicable_tier = tier
                break
        
        if applicable_tier:
            discount_percent = applicable_tier.get("discount_percent", 0)
            discount_amount = final_price * (discount_percent / 100)
            final_price -= discount_amount
            discounts_applied.append({
                "name": vd.name,
                "discount": f"{discount_percent}%",
                "savings": discount_amount
            })
    
    # Check price rules
    rules = db.query(PriceRule).filter(
        PriceRule.is_active == True,
        (PriceRule.product_id == product_id) | (PriceRule.category_id == product.category_id)
    ).order_by(PriceRule.priority.desc()).all()
    
    for rule in rules:
        if rule.min_quantity and quantity < rule.min_quantity:
            continue
        if rule.customer_tier and rule.customer_tier != customer_tier:
            continue
        
        now = datetime.utcnow()
        if rule.start_date and now < rule.start_date:
            continue
        if rule.end_date and now > rule.end_date:
            continue
        
        if rule.discount_type == "percent":
            discount = final_price * (rule.discount_value / 100)
        elif rule.discount_type == "fixed":
            discount = rule.discount_value
        else:
            discount = 0
        
        final_price -= discount
        discounts_applied.append({
            "name": rule.name,
            "discount": f"{rule.discount_value}{'%' if rule.discount_type == 'percent' else ''}",
            "savings": discount
        })
        
        if not rule.stackable:
            break
    
    return {
        "product_id": product_id,
        "quantity": quantity,
        "base_price": base_price,
        "base_total": base_price * quantity,
        "final_price": max(0, final_price),
        "total_savings": (base_price * quantity) - final_price,
        "discounts_applied": discounts_applied
    }
