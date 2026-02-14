# Wine Vintages Router - FR-024
# Manage wine vintages, ratings, and wine club

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.wine_vintage import WineVintage, WineClubMember
from app.models import Product, Category

router = APIRouter(prefix="/wine", tags=["wine"])


# Schemas
class VintageCreate(BaseModel):
    product_id: int
    vintage_year: int
    region: Optional[str] = None
    appellation: Optional[str] = None
    vineyard: Optional[str] = None
    critic_score: Optional[float] = None
    critic_source: Optional[str] = None
    house_rating: Optional[float] = None
    grape_varieties: Optional[str] = None
    aging_potential: Optional[str] = None
    drink_window_start: Optional[int] = None
    drink_window_end: Optional[int] = None
    vintage_stock: int = 0
    vintage_price: Optional[float] = None
    is_allocated: bool = False
    is_library: bool = False


class VintageUpdate(BaseModel):
    critic_score: Optional[float] = None
    critic_source: Optional[str] = None
    house_rating: Optional[float] = None
    aging_potential: Optional[str] = None
    drink_window_start: Optional[int] = None
    drink_window_end: Optional[int] = None
    vintage_stock: Optional[int] = None
    vintage_price: Optional[float] = None
    is_allocated: Optional[bool] = None
    is_library: Optional[bool] = None


class WineClubCreate(BaseModel):
    customer_id: int
    membership_tier: str = "basic"
    red_preference: bool = True
    white_preference: bool = True
    sparkling_preference: bool = False
    bottles_per_shipment: int = 2


# Vintage endpoints
@router.post("/vintages")
def create_vintage(vintage: VintageCreate, db: Session = Depends(get_db)):
    """Create a new wine vintage entry"""
    # Verify product exists and is wine
    product = db.query(Product).filter(Product.id == vintage.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_vintage = WineVintage(**vintage.dict())
    db.add(db_vintage)
    db.commit()
    db.refresh(db_vintage)
    return db_vintage


@router.get("/vintages")
def list_vintages(
    product_id: Optional[int] = None,
    year: Optional[int] = None,
    min_score: Optional[float] = None,
    is_library: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List wine vintages with filters"""
    query = db.query(WineVintage)
    
    if product_id:
        query = query.filter(WineVintage.product_id == product_id)
    if year:
        query = query.filter(WineVintage.vintage_year == year)
    if min_score:
        query = query.filter(WineVintage.critic_score >= min_score)
    if is_library is not None:
        query = query.filter(WineVintage.is_library == is_library)
    
    return query.order_by(desc(WineVintage.vintage_year)).all()


@router.get("/vintages/{vintage_id}")
def get_vintage(vintage_id: int, db: Session = Depends(get_db)):
    """Get specific vintage details"""
    vintage = db.query(WineVintage).filter(WineVintage.id == vintage_id).first()
    if not vintage:
        raise HTTPException(status_code=404, detail="Vintage not found")
    return vintage


@router.patch("/vintages/{vintage_id}")
def update_vintage(vintage_id: int, update: VintageUpdate, db: Session = Depends(get_db)):
    """Update vintage information"""
    vintage = db.query(WineVintage).filter(WineVintage.id == vintage_id).first()
    if not vintage:
        raise HTTPException(status_code=404, detail="Vintage not found")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(vintage, field, value)
    
    db.commit()
    db.refresh(vintage)
    return vintage


@router.get("/vintages/drinking-now")
def get_drinking_now(db: Session = Depends(get_db)):
    """Get wines in their optimal drinking window"""
    current_year = datetime.now().year
    
    vintages = db.query(WineVintage).filter(
        WineVintage.drink_window_start <= current_year,
        WineVintage.drink_window_end >= current_year,
        WineVintage.vintage_stock > 0
    ).all()
    
    return {"drinking_now": vintages}


@router.get("/vintages/highly-rated")
def get_highly_rated(min_score: float = 90, limit: int = 20, db: Session = Depends(get_db)):
    """Get highly rated wines"""
    vintages = db.query(WineVintage).filter(
        WineVintage.critic_score >= min_score
    ).order_by(desc(WineVintage.critic_score)).limit(limit).all()
    
    return {"highly_rated": vintages}


@router.get("/library-selection")
def get_library_selection(db: Session = Depends(get_db)):
    """Get library/rare wine selection"""
    vintages = db.query(WineVintage).filter(
        WineVintage.is_library == True,
        WineVintage.vintage_stock > 0
    ).order_by(desc(WineVintage.vintage_year)).all()
    
    return {"library_selection": vintages}


# Wine Club endpoints
@router.post("/club/members")
def create_wine_club_member(member: WineClubCreate, db: Session = Depends(get_db)):
    """Add customer to wine club"""
    # Check if already a member
    existing = db.query(WineClubMember).filter(
        WineClubMember.customer_id == member.customer_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer already a wine club member")
    
    db_member = WineClubMember(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.get("/club/members")
def list_wine_club_members(
    tier: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """List wine club members"""
    query = db.query(WineClubMember).filter(WineClubMember.is_active == is_active)
    
    if tier:
        query = query.filter(WineClubMember.membership_tier == tier)
    
    return query.order_by(desc(WineClubMember.allocation_priority)).all()


@router.get("/club/members/{member_id}")
def get_wine_club_member(member_id: int, db: Session = Depends(get_db)):
    """Get wine club member details"""
    member = db.query(WineClubMember).filter(WineClubMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Wine club member not found")
    return member


@router.patch("/club/members/{member_id}/upgrade")
def upgrade_membership(member_id: int, new_tier: str, db: Session = Depends(get_db)):
    """Upgrade wine club membership tier"""
    member = db.query(WineClubMember).filter(WineClubMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Wine club member not found")
    
    tier_priority = {"basic": 1, "premium": 2, "reserve": 3}
    member.membership_tier = new_tier
    member.allocation_priority = tier_priority.get(new_tier, 1)
    
    db.commit()
    db.refresh(member)
    return member


@router.get("/club/allocation-list")
def get_allocation_list(db: Session = Depends(get_db)):
    """Get wine club members sorted by allocation priority"""
    members = db.query(WineClubMember).filter(
        WineClubMember.is_active == True
    ).order_by(
        desc(WineClubMember.allocation_priority),
        WineClubMember.join_date
    ).all()
    
    return {
        "allocation_order": [
            {
                "member_id": m.id,
                "customer_id": m.customer_id,
                "tier": m.membership_tier,
                "priority": m.allocation_priority,
                "join_date": m.join_date.isoformat() if m.join_date else None
            }
            for m in members
        ]
    }
