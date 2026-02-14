# Seasonal Promotions Router - FR-040
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.seasonal_promo import SeasonalPromotion, SeasonalBundle

router = APIRouter(prefix="/seasonal", tags=["seasonal"])


class PromoCreate(BaseModel):
    name: str
    description: Optional[str] = None
    occasion: str
    start_date: datetime
    end_date: datetime
    category_ids: Optional[str] = None
    product_ids: Optional[str] = None
    discount_type: str = "percent"
    discount_value: float
    minimum_purchase: Optional[float] = None
    max_uses: Optional[int] = None
    banner_text: Optional[str] = None


class BundleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    occasion: str
    product_ids: str
    regular_price: float
    bundle_price: float
    includes_gift_wrap: bool = False
    includes_gift_bag: bool = False
    stock_quantity: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Promotion endpoints
@router.post("/promotions")
def create_promotion(promo: PromoCreate, db: Session = Depends(get_db)):
    """Create a seasonal promotion"""
    db_promo = SeasonalPromotion(
        **promo.dict(),
        savings=None,
        is_active=True
    )
    db.add(db_promo)
    db.commit()
    db.refresh(db_promo)
    return db_promo


@router.get("/promotions")
def list_promotions(
    occasion: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List seasonal promotions"""
    query = db.query(SeasonalPromotion)
    
    if active_only:
        now = datetime.utcnow()
        query = query.filter(
            SeasonalPromotion.is_active == True,
            SeasonalPromotion.start_date <= now,
            SeasonalPromotion.end_date >= now
        )
    
    if occasion:
        query = query.filter(SeasonalPromotion.occasion == occasion)
    
    return query.order_by(desc(SeasonalPromotion.display_priority)).all()


@router.get("/promotions/current")
def get_current_promotions(db: Session = Depends(get_db)):
    """Get all currently active promotions"""
    now = datetime.utcnow()
    
    promos = db.query(SeasonalPromotion).filter(
        SeasonalPromotion.is_active == True,
        SeasonalPromotion.start_date <= now,
        SeasonalPromotion.end_date >= now
    ).all()
    
    return {
        "promotions": promos,
        "count": len(promos)
    }


@router.get("/promotions/{promo_id}")
def get_promotion(promo_id: int, db: Session = Depends(get_db)):
    """Get promotion details"""
    promo = db.query(SeasonalPromotion).filter(SeasonalPromotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promo


@router.post("/promotions/{promo_id}/use")
def use_promotion(promo_id: int, db: Session = Depends(get_db)):
    """Record promotion use"""
    promo = db.query(SeasonalPromotion).filter(SeasonalPromotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    if promo.max_uses and promo.current_uses >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promotion usage limit reached")
    
    promo.current_uses += 1
    db.commit()
    
    return {"uses": promo.current_uses, "remaining": promo.max_uses - promo.current_uses if promo.max_uses else None}


# Bundle endpoints
@router.post("/bundles")
def create_bundle(bundle: BundleCreate, db: Session = Depends(get_db)):
    """Create a holiday gift bundle"""
    savings = bundle.regular_price - bundle.bundle_price
    
    db_bundle = SeasonalBundle(
        **bundle.dict(),
        savings=savings,
        is_active=True
    )
    db.add(db_bundle)
    db.commit()
    db.refresh(db_bundle)
    return db_bundle


@router.get("/bundles")
def list_bundles(
    occasion: Optional[str] = None,
    in_stock: bool = False,
    db: Session = Depends(get_db)
):
    """List seasonal bundles"""
    query = db.query(SeasonalBundle).filter(SeasonalBundle.is_active == True)
    
    if occasion:
        query = query.filter(SeasonalBundle.occasion == occasion)
    if in_stock:
        query = query.filter(SeasonalBundle.stock_quantity > 0)
    
    return query.all()


@router.get("/bundles/{bundle_id}")
def get_bundle(bundle_id: int, db: Session = Depends(get_db)):
    """Get bundle details"""
    bundle = db.query(SeasonalBundle).filter(SeasonalBundle.id == bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.post("/bundles/{bundle_id}/purchase")
def purchase_bundle(bundle_id: int, quantity: int = 1, db: Session = Depends(get_db)):
    """Purchase a bundle"""
    bundle = db.query(SeasonalBundle).filter(SeasonalBundle.id == bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    if bundle.stock_quantity < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    bundle.stock_quantity -= quantity
    db.commit()
    
    return {
        "purchased": quantity,
        "total": bundle.bundle_price * quantity,
        "remaining_stock": bundle.stock_quantity
    }


@router.get("/occasions")
def list_occasions():
    """List available occasions"""
    return {
        "occasions": [
            {"id": "new_year", "name": "New Year's", "typical_start": "12-26", "typical_end": "01-02"},
            {"id": "valentines", "name": "Valentine's Day", "typical_start": "02-01", "typical_end": "02-14"},
            {"id": "st_patricks", "name": "St. Patrick's Day", "typical_start": "03-01", "typical_end": "03-17"},
            {"id": "memorial_day", "name": "Memorial Day", "typical_start": "05-20", "typical_end": "05-31"},
            {"id": "july_4th", "name": "Fourth of July", "typical_start": "06-25", "typical_end": "07-04"},
            {"id": "labor_day", "name": "Labor Day", "typical_start": "08-25", "typical_end": "09-05"},
            {"id": "halloween", "name": "Halloween", "typical_start": "10-01", "typical_end": "10-31"},
            {"id": "thanksgiving", "name": "Thanksgiving", "typical_start": "11-15", "typical_end": "11-28"},
            {"id": "christmas", "name": "Christmas/Holiday", "typical_start": "12-01", "typical_end": "12-25"},
            {"id": "other", "name": "Other/Custom", "typical_start": None, "typical_end": None}
        ]
    }


@router.get("/calendar")
def seasonal_calendar(db: Session = Depends(get_db)):
    """Get upcoming seasonal promotions calendar"""
    now = datetime.utcnow()
    
    promos = db.query(SeasonalPromotion).filter(
        SeasonalPromotion.is_active == True,
        SeasonalPromotion.end_date >= now
    ).order_by(SeasonalPromotion.start_date).all()
    
    return {
        "current_date": now.isoformat(),
        "upcoming": [
            {
                "id": p.id,
                "name": p.name,
                "occasion": p.occasion,
                "start": p.start_date.isoformat(),
                "end": p.end_date.isoformat(),
                "is_active": p.start_date <= now <= p.end_date
            }
            for p in promos
        ]
    }
