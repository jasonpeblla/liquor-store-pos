# Taste Profile Router - FR-029
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.spirits_profile import CustomerTasteProfile, ProductRecommendation
from app.models import Product, Category

router = APIRouter(prefix="/taste-profile", tags=["taste-profile"])


class TasteProfileCreate(BaseModel):
    customer_id: int
    prefers_red: bool = False
    prefers_white: bool = False
    prefers_sparkling: bool = False
    prefers_whiskey: bool = False
    prefers_vodka: bool = False
    prefers_gin: bool = False
    prefers_rum: bool = False
    prefers_tequila: bool = False
    prefers_lager: bool = False
    prefers_ale: bool = False
    prefers_ipa: bool = False
    wine_sweetness: Optional[str] = None
    wine_body: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    prefers_organic: bool = False
    flavor_notes: Optional[str] = None
    favorite_regions: Optional[str] = None


@router.post("/")
def create_taste_profile(profile: TasteProfileCreate, db: Session = Depends(get_db)):
    """Create customer taste profile"""
    existing = db.query(CustomerTasteProfile).filter(
        CustomerTasteProfile.customer_id == profile.customer_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists")
    
    db_profile = CustomerTasteProfile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/{customer_id}")
def get_taste_profile(customer_id: int, db: Session = Depends(get_db)):
    """Get customer taste profile"""
    profile = db.query(CustomerTasteProfile).filter(
        CustomerTasteProfile.customer_id == customer_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{customer_id}")
def update_taste_profile(customer_id: int, updates: dict, db: Session = Depends(get_db)):
    """Update taste profile"""
    profile = db.query(CustomerTasteProfile).filter(
        CustomerTasteProfile.customer_id == customer_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    for key, value in updates.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{customer_id}/recommendations")
def get_recommendations(customer_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Get personalized product recommendations"""
    profile = db.query(CustomerTasteProfile).filter(
        CustomerTasteProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        # Return popular products if no profile
        products = db.query(Product).limit(limit).all()
        return {"recommendations": products, "personalized": False}
    
    # Build recommendation based on preferences
    recommendations = []
    
    # Wine recommendations
    if profile.prefers_red or profile.prefers_white:
        wine_cat = db.query(Category).filter(Category.name == "Wine").first()
        if wine_cat:
            wines = db.query(Product).filter(Product.category_id == wine_cat.id).limit(5).all()
            for w in wines:
                recommendations.append({
                    "product": w,
                    "reason": "Matches your wine preferences",
                    "score": 0.8
                })
    
    # Spirits recommendations
    spirits_cat = db.query(Category).filter(Category.name == "Spirits").first()
    if spirits_cat:
        if profile.prefers_whiskey:
            whiskeys = db.query(Product).filter(
                Product.category_id == spirits_cat.id,
                Product.name.ilike("%whiskey%") | Product.name.ilike("%bourbon%")
            ).limit(3).all()
            for w in whiskeys:
                recommendations.append({
                    "product": w,
                    "reason": "You enjoy whiskey",
                    "score": 0.9
                })
    
    # Filter by budget
    if profile.budget_max:
        recommendations = [r for r in recommendations if r["product"].price <= profile.budget_max]
    
    return {
        "recommendations": recommendations[:limit],
        "personalized": True,
        "profile_id": profile.id
    }


@router.post("/{customer_id}/quick-quiz")
def quick_taste_quiz(
    customer_id: int,
    sweet_vs_dry: str,  # sweet, balanced, dry
    adventurous: bool,
    price_sensitivity: str,  # budget, moderate, premium
    db: Session = Depends(get_db)
):
    """Quick quiz to build initial taste profile"""
    profile = db.query(CustomerTasteProfile).filter(
        CustomerTasteProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        profile = CustomerTasteProfile(customer_id=customer_id)
        db.add(profile)
    
    # Set preferences based on quiz
    if sweet_vs_dry == "sweet":
        profile.wine_sweetness = "sweet"
        profile.prefers_white = True
        profile.prefers_rum = True
    elif sweet_vs_dry == "dry":
        profile.wine_sweetness = "dry"
        profile.prefers_red = True
        profile.prefers_whiskey = True
        profile.prefers_gin = True
    else:
        profile.wine_sweetness = "off-dry"
        profile.prefers_white = True
        profile.prefers_vodka = True
    
    if adventurous:
        profile.prefers_ipa = True
        profile.prefers_sour = True
        profile.prefers_tequila = True
    
    # Budget
    if price_sensitivity == "budget":
        profile.budget_max = 20.0
    elif price_sensitivity == "moderate":
        profile.budget_min = 15.0
        profile.budget_max = 50.0
    else:
        profile.budget_min = 40.0
    
    db.commit()
    db.refresh(profile)
    return {"profile": profile, "message": "Profile created from quiz"}
