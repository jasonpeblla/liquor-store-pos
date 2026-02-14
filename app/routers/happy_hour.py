from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, time

from app.database import get_db
from app.models.happy_hour import HappyHour
from app.models.product import Product
from app.models.category import Category

router = APIRouter(prefix="/happy-hour", tags=["happy-hour"])


# Schemas
class HappyHourCreate(BaseModel):
    name: str
    start_time: str  # "16:00"
    end_time: str    # "19:00"
    monday: bool = False
    tuesday: bool = False
    wednesday: bool = False
    thursday: bool = False
    friday: bool = False
    saturday: bool = False
    sunday: bool = False
    discount_type: str = "percentage"  # percentage, fixed, price
    discount_value: float = 10.0
    applies_to: str = "all"  # all, category, product
    category_id: Optional[int] = None
    product_ids: Optional[List[int]] = None
    max_quantity_per_customer: Optional[int] = None
    min_purchase: float = 0.0
    exclude_case_pricing: bool = True


class HappyHourUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    monday: Optional[bool] = None
    tuesday: Optional[bool] = None
    wednesday: Optional[bool] = None
    thursday: Optional[bool] = None
    friday: Optional[bool] = None
    saturday: Optional[bool] = None
    sunday: Optional[bool] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    applies_to: Optional[str] = None
    category_id: Optional[int] = None
    product_ids: Optional[List[int]] = None
    max_quantity_per_customer: Optional[int] = None
    min_purchase: Optional[float] = None
    exclude_case_pricing: Optional[bool] = None
    is_active: Optional[bool] = None


class HappyHourResponse(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    discount_type: str
    discount_value: float
    applies_to: str
    category_id: Optional[int]
    product_ids: Optional[List[int]]
    max_quantity_per_customer: Optional[int]
    min_purchase: float
    exclude_case_pricing: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActiveHappyHourResponse(BaseModel):
    is_active: bool
    happy_hours: List[HappyHourResponse]
    message: str


def parse_time(time_str: str) -> time:
    """Parse time string like '16:00' to time object"""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def is_day_active(hh: HappyHour, weekday: int) -> bool:
    """Check if happy hour is active on given weekday (0=Monday)"""
    day_map = {
        0: hh.monday,
        1: hh.tuesday,
        2: hh.wednesday,
        3: hh.thursday,
        4: hh.friday,
        5: hh.saturday,
        6: hh.sunday
    }
    return day_map.get(weekday, False)


# Routes
@router.get("", response_model=List[HappyHourResponse])
def list_happy_hours(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all happy hour configurations"""
    query = db.query(HappyHour)
    if active_only:
        query = query.filter(HappyHour.is_active == True)
    return query.all()


@router.get("/active", response_model=ActiveHappyHourResponse)
def get_active_happy_hours(db: Session = Depends(get_db)):
    """Check if any happy hour is currently active"""
    now = datetime.now()
    current_time = now.time()
    current_weekday = now.weekday()
    
    all_hh = db.query(HappyHour).filter(HappyHour.is_active == True).all()
    active_hh = []
    
    for hh in all_hh:
        if not is_day_active(hh, current_weekday):
            continue
        
        start = parse_time(hh.start_time)
        end = parse_time(hh.end_time)
        
        # Handle overnight happy hours
        if start <= end:
            if start <= current_time <= end:
                active_hh.append(hh)
        else:
            if current_time >= start or current_time <= end:
                active_hh.append(hh)
    
    if active_hh:
        return {
            "is_active": True,
            "happy_hours": active_hh,
            "message": f"{len(active_hh)} happy hour(s) currently active!"
        }
    else:
        return {
            "is_active": False,
            "happy_hours": [],
            "message": "No happy hour active right now"
        }


@router.get("/{hh_id}", response_model=HappyHourResponse)
def get_happy_hour(hh_id: int, db: Session = Depends(get_db)):
    """Get specific happy hour by ID"""
    hh = db.query(HappyHour).filter(HappyHour.id == hh_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")
    return hh


@router.post("", response_model=HappyHourResponse)
def create_happy_hour(data: HappyHourCreate, db: Session = Depends(get_db)):
    """Create a new happy hour"""
    hh = HappyHour(**data.model_dump())
    db.add(hh)
    db.commit()
    db.refresh(hh)
    return hh


@router.patch("/{hh_id}", response_model=HappyHourResponse)
def update_happy_hour(hh_id: int, data: HappyHourUpdate, db: Session = Depends(get_db)):
    """Update a happy hour"""
    hh = db.query(HappyHour).filter(HappyHour.id == hh_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hh, key, value)
    
    db.commit()
    db.refresh(hh)
    return hh


@router.delete("/{hh_id}")
def delete_happy_hour(hh_id: int, db: Session = Depends(get_db)):
    """Delete a happy hour"""
    hh = db.query(HappyHour).filter(HappyHour.id == hh_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")
    
    db.delete(hh)
    db.commit()
    return {"message": "Happy hour deleted", "id": hh_id}


@router.post("/{hh_id}/toggle")
def toggle_happy_hour(hh_id: int, db: Session = Depends(get_db)):
    """Toggle happy hour active status"""
    hh = db.query(HappyHour).filter(HappyHour.id == hh_id).first()
    if not hh:
        raise HTTPException(status_code=404, detail="Happy hour not found")
    
    hh.is_active = not hh.is_active
    db.commit()
    return {"message": f"Happy hour {'activated' if hh.is_active else 'deactivated'}", "is_active": hh.is_active}


@router.post("/calculate-discount")
def calculate_happy_hour_discount(
    product_id: int,
    quantity: int = 1,
    is_case_price: bool = False,
    db: Session = Depends(get_db)
):
    """Calculate happy hour discount for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get active happy hours
    now = datetime.now()
    current_time = now.time()
    current_weekday = now.weekday()
    
    all_hh = db.query(HappyHour).filter(HappyHour.is_active == True).all()
    
    best_discount = 0
    applied_hh = None
    
    for hh in all_hh:
        # Check day
        if not is_day_active(hh, current_weekday):
            continue
        
        # Check time
        start = parse_time(hh.start_time)
        end = parse_time(hh.end_time)
        
        if start <= end:
            if not (start <= current_time <= end):
                continue
        else:
            if not (current_time >= start or current_time <= end):
                continue
        
        # Check if this HH applies to the product
        if hh.applies_to == "category" and product.category_id != hh.category_id:
            continue
        if hh.applies_to == "product" and hh.product_ids and product.id not in hh.product_ids:
            continue
        
        # Skip if case pricing and exclude_case_pricing is True
        if is_case_price and hh.exclude_case_pricing:
            continue
        
        # Calculate discount
        original_price = product.price
        if hh.discount_type == "percentage":
            discount = original_price * (hh.discount_value / 100)
        elif hh.discount_type == "fixed":
            discount = hh.discount_value
        elif hh.discount_type == "price":
            discount = original_price - hh.discount_value
        else:
            discount = 0
        
        if discount > best_discount:
            best_discount = discount
            applied_hh = hh
    
    if applied_hh:
        return {
            "product_id": product_id,
            "product_name": product.name,
            "original_price": product.price,
            "discount_per_unit": round(best_discount, 2),
            "final_price": round(product.price - best_discount, 2),
            "quantity": quantity,
            "total_savings": round(best_discount * quantity, 2),
            "happy_hour_name": applied_hh.name,
            "happy_hour_id": applied_hh.id
        }
    else:
        return {
            "product_id": product_id,
            "product_name": product.name,
            "original_price": product.price,
            "discount_per_unit": 0,
            "final_price": product.price,
            "quantity": quantity,
            "total_savings": 0,
            "happy_hour_name": None,
            "happy_hour_id": None,
            "message": "No happy hour discount applicable"
        }
