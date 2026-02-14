from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.mix_match import MixMatchDeal
from app.models.product import Product

router = APIRouter(prefix="/mix-match", tags=["mix-match"])


# Schemas
class MixMatchCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_ids: Optional[List[int]] = None
    product_ids: Optional[List[int]] = None
    brand_filter: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    quantity_required: int
    discount_type: str = "percentage"
    discount_value: float
    stackable: bool = False
    max_applications: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: int = 0


class MixMatchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_ids: Optional[List[int]] = None
    product_ids: Optional[List[int]] = None
    brand_filter: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    quantity_required: Optional[int] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    stackable: Optional[bool] = None
    max_applications: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class MixMatchResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category_ids: Optional[List[int]]
    product_ids: Optional[List[int]]
    brand_filter: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    quantity_required: int
    discount_type: str
    discount_value: float
    stackable: bool
    max_applications: Optional[int]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class CalculateRequest(BaseModel):
    items: List[CartItem]


class AppliedDeal(BaseModel):
    deal_id: int
    deal_name: str
    qualifying_products: List[int]
    quantity_used: int
    discount_amount: float


class CalculateResponse(BaseModel):
    applicable_deals: List[AppliedDeal]
    total_discount: float
    message: str


def is_deal_active(deal: MixMatchDeal) -> bool:
    """Check if deal is currently active based on dates"""
    now = datetime.utcnow()
    if deal.start_date and now < deal.start_date:
        return False
    if deal.end_date and now > deal.end_date:
        return False
    return deal.is_active


def product_qualifies(product: Product, deal: MixMatchDeal) -> bool:
    """Check if a product qualifies for a deal"""
    # Check category
    if deal.category_ids and product.category_id not in deal.category_ids:
        return False
    
    # Check specific products
    if deal.product_ids and product.id not in deal.product_ids:
        return False
    
    # Check brand
    if deal.brand_filter and product.brand and deal.brand_filter.lower() not in product.brand.lower():
        return False
    
    # Check price range
    if deal.min_price and product.price < deal.min_price:
        return False
    if deal.max_price and product.price > deal.max_price:
        return False
    
    return True


# Routes
@router.get("", response_model=List[MixMatchResponse])
def list_deals(
    active_only: bool = True,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List all mix-and-match deals"""
    query = db.query(MixMatchDeal)
    
    if active_only:
        query = query.filter(MixMatchDeal.is_active == True)
    
    deals = query.order_by(MixMatchDeal.priority.desc()).all()
    
    # Filter by active dates
    if active_only:
        deals = [d for d in deals if is_deal_active(d)]
    
    return deals


@router.get("/{deal_id}", response_model=MixMatchResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """Get a specific deal"""
    deal = db.query(MixMatchDeal).filter(MixMatchDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("", response_model=MixMatchResponse)
def create_deal(data: MixMatchCreate, db: Session = Depends(get_db)):
    """Create a new mix-and-match deal"""
    deal = MixMatchDeal(**data.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.patch("/{deal_id}", response_model=MixMatchResponse)
def update_deal(deal_id: int, data: MixMatchUpdate, db: Session = Depends(get_db)):
    """Update a deal"""
    deal = db.query(MixMatchDeal).filter(MixMatchDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(deal, key, value)
    
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}")
def delete_deal(deal_id: int, db: Session = Depends(get_db)):
    """Delete a deal"""
    deal = db.query(MixMatchDeal).filter(MixMatchDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    db.delete(deal)
    db.commit()
    return {"message": "Deal deleted", "id": deal_id}


@router.post("/calculate", response_model=CalculateResponse)
def calculate_discounts(data: CalculateRequest, db: Session = Depends(get_db)):
    """Calculate mix-and-match discounts for a cart"""
    # Get all active deals
    deals = db.query(MixMatchDeal).filter(MixMatchDeal.is_active == True).order_by(
        MixMatchDeal.priority.desc()
    ).all()
    deals = [d for d in deals if is_deal_active(d)]
    
    # Get all products in cart
    product_ids = [item.product_id for item in data.items]
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    
    # Track which items have been used for deals
    item_usage: Dict[int, int] = {item.product_id: item.quantity for item in data.items}
    item_prices: Dict[int, float] = {item.product_id: item.unit_price for item in data.items}
    
    applied_deals: List[AppliedDeal] = []
    total_discount = 0.0
    
    for deal in deals:
        # Find qualifying items for this deal
        qualifying_items = []
        for product_id, remaining_qty in item_usage.items():
            if remaining_qty <= 0:
                continue
            product = products.get(product_id)
            if product and product_qualifies(product, deal):
                qualifying_items.append((product_id, remaining_qty, item_prices[product_id]))
        
        if not qualifying_items:
            continue
        
        # Calculate how many times this deal can be applied
        total_qualifying_qty = sum(qty for _, qty, _ in qualifying_items)
        times_applicable = total_qualifying_qty // deal.quantity_required
        
        if deal.max_applications:
            times_applicable = min(times_applicable, deal.max_applications)
        
        if times_applicable <= 0:
            continue
        
        # Apply the deal
        qty_needed = deal.quantity_required * times_applicable
        qty_used = 0
        deal_items = []
        items_for_discount = []
        
        for product_id, remaining_qty, price in qualifying_items:
            if qty_used >= qty_needed:
                break
            take = min(remaining_qty, qty_needed - qty_used)
            qty_used += take
            deal_items.append(product_id)
            items_for_discount.extend([price] * take)
            
            if not deal.stackable:
                item_usage[product_id] = remaining_qty - take
        
        # Calculate discount
        discount = 0.0
        if deal.discount_type == "percentage":
            discount = sum(items_for_discount) * (deal.discount_value / 100)
        elif deal.discount_type == "fixed_per_item":
            discount = deal.discount_value * len(items_for_discount)
        elif deal.discount_type == "fixed_total":
            discount = deal.discount_value * times_applicable
        
        if discount > 0:
            applied_deals.append(AppliedDeal(
                deal_id=deal.id,
                deal_name=deal.name,
                qualifying_products=list(set(deal_items)),
                quantity_used=qty_used,
                discount_amount=round(discount, 2)
            ))
            total_discount += discount
    
    message = f"Applied {len(applied_deals)} mix-and-match deal(s)" if applied_deals else "No mix-and-match deals applicable"
    
    return CalculateResponse(
        applicable_deals=applied_deals,
        total_discount=round(total_discount, 2),
        message=message
    )


@router.get("/for-product/{product_id}")
def get_deals_for_product(product_id: int, db: Session = Depends(get_db)):
    """Get all deals that a product qualifies for"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    deals = db.query(MixMatchDeal).filter(MixMatchDeal.is_active == True).all()
    deals = [d for d in deals if is_deal_active(d) and product_qualifies(product, d)]
    
    return {
        "product_id": product_id,
        "product_name": product.name,
        "qualifying_deals": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "quantity_required": d.quantity_required,
                "discount_type": d.discount_type,
                "discount_value": d.discount_value
            }
            for d in deals
        ]
    }
