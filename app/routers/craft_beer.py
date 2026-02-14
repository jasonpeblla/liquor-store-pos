# Craft Beer Router - FR-025
# Manage kegs, taps, and growler fills

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.craft_beer import Keg, GrowlerFill, TapRotation

router = APIRouter(prefix="/craft-beer", tags=["craft-beer"])


# Schemas
class KegCreate(BaseModel):
    product_id: int
    supplier_id: Optional[int] = None
    keg_size: str = "1/2"
    capacity_oz: float = 1984
    keg_cost: float = 0.0
    price_per_oz: float = 0.0
    growler_32_price: float = 0.0
    growler_64_price: float = 0.0
    pint_price: float = 0.0
    taster_price: float = 0.0
    deposit_amount: float = 0.0
    style: Optional[str] = None
    ibu: Optional[int] = None
    abv: Optional[float] = None
    description: Optional[str] = None


class TapKeg(BaseModel):
    tap_number: int


class GrowlerFillCreate(BaseModel):
    keg_id: int
    size_oz: float
    customer_id: Optional[int] = None
    container_type: str = "house"
    is_refill: bool = False


# Keg endpoints
@router.post("/kegs")
def create_keg(keg: KegCreate, db: Session = Depends(get_db)):
    """Register a new keg"""
    db_keg = Keg(**keg.dict(), remaining_oz=keg.capacity_oz)
    db.add(db_keg)
    db.commit()
    db.refresh(db_keg)
    return db_keg


@router.get("/kegs")
def list_kegs(
    status: Optional[str] = None,
    on_tap: bool = False,
    db: Session = Depends(get_db)
):
    """List kegs with filters"""
    query = db.query(Keg)
    
    if status:
        query = query.filter(Keg.status == status)
    if on_tap:
        query = query.filter(Keg.tap_number.isnot(None), Keg.status == "on_tap")
    
    return query.order_by(desc(Keg.created_at)).all()


@router.get("/kegs/{keg_id}")
def get_keg(keg_id: int, db: Session = Depends(get_db)):
    """Get keg details"""
    keg = db.query(Keg).filter(Keg.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    return keg


@router.post("/kegs/{keg_id}/tap")
def tap_keg(keg_id: int, tap: TapKeg, db: Session = Depends(get_db)):
    """Put a keg on tap"""
    keg = db.query(Keg).filter(Keg.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    
    # Check if tap is occupied
    existing = db.query(Keg).filter(
        Keg.tap_number == tap.tap_number,
        Keg.status == "on_tap"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tap {tap.tap_number} is already occupied")
    
    keg.tap_number = tap.tap_number
    keg.status = "on_tap"
    keg.tapped_date = datetime.utcnow()
    
    # Create rotation record
    rotation = TapRotation(
        tap_number=tap.tap_number,
        keg_id=keg_id,
        tapped_at=datetime.utcnow()
    )
    db.add(rotation)
    db.commit()
    db.refresh(keg)
    
    return {"message": f"Keg {keg_id} now on tap {tap.tap_number}", "keg": keg}


@router.post("/kegs/{keg_id}/kick")
def kick_keg(keg_id: int, db: Session = Depends(get_db)):
    """Mark a keg as kicked (empty)"""
    keg = db.query(Keg).filter(Keg.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    
    tap_number = keg.tap_number
    keg.status = "kicked"
    keg.tap_number = None
    keg.remaining_oz = 0
    
    # Update rotation record
    rotation = db.query(TapRotation).filter(
        TapRotation.keg_id == keg_id,
        TapRotation.kicked_at.is_(None)
    ).first()
    if rotation:
        rotation.kicked_at = datetime.utcnow()
        rotation.days_on_tap = (datetime.utcnow() - rotation.tapped_at).days
    
    db.commit()
    return {"message": f"Keg {keg_id} kicked from tap {tap_number}"}


# Growler Fill endpoints
@router.post("/fills")
def create_growler_fill(fill: GrowlerFillCreate, db: Session = Depends(get_db)):
    """Record a growler fill"""
    keg = db.query(Keg).filter(Keg.id == fill.keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    
    if keg.remaining_oz < fill.size_oz:
        raise HTTPException(status_code=400, detail="Not enough beer remaining in keg")
    
    # Calculate price
    if fill.size_oz == 32:
        price = keg.growler_32_price
    elif fill.size_oz == 64:
        price = keg.growler_64_price
    else:
        price = fill.size_oz * keg.price_per_oz
    
    # Apply refill discount
    if fill.is_refill:
        price = price * 0.8  # 20% off refills
    
    db_fill = GrowlerFill(
        keg_id=fill.keg_id,
        customer_id=fill.customer_id,
        size_oz=fill.size_oz,
        price=price,
        container_type=fill.container_type,
        is_refill=fill.is_refill
    )
    db.add(db_fill)
    
    # Update keg
    keg.remaining_oz -= fill.size_oz
    
    db.commit()
    db.refresh(db_fill)
    
    return {
        "fill": db_fill,
        "keg_remaining_oz": keg.remaining_oz
    }


# Tap List
@router.get("/tap-list")
def get_tap_list(db: Session = Depends(get_db)):
    """Get current tap list for display"""
    kegs = db.query(Keg).filter(
        Keg.status == "on_tap",
        Keg.tap_number.isnot(None)
    ).order_by(Keg.tap_number).all()
    
    return {
        "tap_list": [
            {
                "tap": k.tap_number,
                "keg_id": k.id,
                "product_id": k.product_id,
                "style": k.style,
                "abv": k.abv,
                "ibu": k.ibu,
                "description": k.description,
                "pint_price": k.pint_price,
                "growler_32_price": k.growler_32_price,
                "growler_64_price": k.growler_64_price,
                "remaining_percent": round((k.remaining_oz / k.capacity_oz) * 100, 1)
            }
            for k in kegs
        ]
    }


@router.get("/inventory")
def get_beer_inventory(db: Session = Depends(get_db)):
    """Get craft beer inventory summary"""
    in_stock = db.query(func.count(Keg.id)).filter(Keg.status == "in_stock").scalar() or 0
    on_tap = db.query(func.count(Keg.id)).filter(Keg.status == "on_tap").scalar() or 0
    kicked = db.query(func.count(Keg.id)).filter(Keg.status == "kicked").scalar() or 0
    
    # Low kegs (< 20% remaining)
    low_kegs = db.query(Keg).filter(
        Keg.status == "on_tap",
        Keg.remaining_oz < Keg.capacity_oz * 0.2
    ).all()
    
    return {
        "summary": {
            "in_stock": in_stock,
            "on_tap": on_tap,
            "kicked": kicked
        },
        "low_kegs": [
            {
                "keg_id": k.id,
                "tap_number": k.tap_number,
                "remaining_percent": round((k.remaining_oz / k.capacity_oz) * 100, 1)
            }
            for k in low_kegs
        ]
    }


@router.get("/rotation-history")
def get_rotation_history(tap_number: Optional[int] = None, limit: int = 20, db: Session = Depends(get_db)):
    """Get tap rotation history"""
    query = db.query(TapRotation)
    
    if tap_number:
        query = query.filter(TapRotation.tap_number == tap_number)
    
    rotations = query.order_by(desc(TapRotation.tapped_at)).limit(limit).all()
    
    return {"rotations": rotations}
