# Store Hours Router - FR-035
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.store_hours import StoreHours, HolidayHours, AlcoholSaleRestriction

router = APIRouter(prefix="/store-hours", tags=["store-hours"])


class HoursUpdate(BaseModel):
    is_open: bool = True
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    alcohol_open_time: Optional[str] = None
    alcohol_close_time: Optional[str] = None


class HolidayCreate(BaseModel):
    date: datetime
    name: str
    is_closed: bool = False
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    note: Optional[str] = None


class RestrictionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    restricted_days: Optional[str] = None
    restricted_start: Optional[str] = None
    restricted_end: Optional[str] = None


# Initialize default hours
@router.post("/initialize")
def initialize_store_hours(db: Session = Depends(get_db)):
    """Initialize default store hours (run once)"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    existing = db.query(StoreHours).count()
    if existing > 0:
        return {"message": "Hours already initialized"}
    
    for i, day in enumerate(days):
        hours = StoreHours(
            day_of_week=i,
            day_name=day,
            is_open=True,
            open_time="09:00" if i < 6 else "10:00",
            close_time="21:00" if i < 6 else "20:00",
            alcohol_open_time="09:00" if i < 6 else "12:00",  # Sunday noon
            alcohol_close_time="21:00" if i < 6 else "20:00"
        )
        db.add(hours)
    
    db.commit()
    return {"message": "Store hours initialized"}


@router.get("/")
def get_store_hours(db: Session = Depends(get_db)):
    """Get all store hours"""
    hours = db.query(StoreHours).order_by(StoreHours.day_of_week).all()
    return hours


@router.get("/today")
def get_today_hours(db: Session = Depends(get_db)):
    """Get today's hours"""
    today = datetime.now()
    day_of_week = today.weekday()
    
    # Check for holiday override
    holiday = db.query(HolidayHours).filter(
        HolidayHours.date >= today.replace(hour=0, minute=0, second=0),
        HolidayHours.date < today.replace(hour=0, minute=0, second=0) + timedelta(days=1)
    ).first()
    
    if holiday:
        return {
            "is_holiday": True,
            "holiday_name": holiday.name,
            "is_closed": holiday.is_closed,
            "open_time": holiday.open_time,
            "close_time": holiday.close_time,
            "note": holiday.note
        }
    
    hours = db.query(StoreHours).filter(StoreHours.day_of_week == day_of_week).first()
    
    if not hours:
        return {"error": "Hours not configured"}
    
    return {
        "is_holiday": False,
        "day": hours.day_name,
        "is_open": hours.is_open,
        "open_time": hours.open_time,
        "close_time": hours.close_time,
        "alcohol_open_time": hours.alcohol_open_time,
        "alcohol_close_time": hours.alcohol_close_time
    }


@router.patch("/{day_of_week}")
def update_hours(day_of_week: int, update: HoursUpdate, db: Session = Depends(get_db)):
    """Update hours for a specific day"""
    hours = db.query(StoreHours).filter(StoreHours.day_of_week == day_of_week).first()
    if not hours:
        raise HTTPException(status_code=404, detail="Day not found")
    
    for key, value in update.dict(exclude_unset=True).items():
        setattr(hours, key, value)
    
    db.commit()
    db.refresh(hours)
    return hours


# Holiday hours
@router.post("/holidays")
def create_holiday(holiday: HolidayCreate, db: Session = Depends(get_db)):
    """Add holiday hours"""
    db_holiday = HolidayHours(**holiday.dict())
    db.add(db_holiday)
    db.commit()
    db.refresh(db_holiday)
    return db_holiday


@router.get("/holidays")
def list_holidays(upcoming_only: bool = True, db: Session = Depends(get_db)):
    """List holidays"""
    query = db.query(HolidayHours)
    if upcoming_only:
        query = query.filter(HolidayHours.date >= datetime.now())
    return query.order_by(HolidayHours.date).all()


@router.delete("/holidays/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    """Delete a holiday"""
    holiday = db.query(HolidayHours).filter(HolidayHours.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(holiday)
    db.commit()
    return {"message": "Holiday deleted"}


# Alcohol restrictions
@router.post("/alcohol-restrictions")
def create_restriction(restriction: RestrictionCreate, db: Session = Depends(get_db)):
    """Create alcohol sale restriction"""
    db_restriction = AlcoholSaleRestriction(**restriction.dict(), is_active=True)
    db.add(db_restriction)
    db.commit()
    db.refresh(db_restriction)
    return db_restriction


@router.get("/alcohol-restrictions")
def list_restrictions(db: Session = Depends(get_db)):
    """List alcohol sale restrictions"""
    return db.query(AlcoholSaleRestriction).filter(AlcoholSaleRestriction.is_active == True).all()


@router.get("/can-sell-alcohol")
def can_sell_alcohol(db: Session = Depends(get_db)):
    """Check if alcohol can be sold right now"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    day_of_week = now.weekday()
    
    # Check restrictions
    restrictions = db.query(AlcoholSaleRestriction).filter(
        AlcoholSaleRestriction.is_active == True
    ).all()
    
    for r in restrictions:
        if r.restricted_days:
            restricted_days = [int(d) for d in r.restricted_days.split(",")]
            if day_of_week in restricted_days:
                if r.restricted_start and r.restricted_end:
                    if r.restricted_start <= current_time <= r.restricted_end:
                        return {
                            "can_sell": False,
                            "reason": r.name,
                            "until": r.restricted_end
                        }
    
    # Check store alcohol hours
    hours = db.query(StoreHours).filter(StoreHours.day_of_week == day_of_week).first()
    if hours and hours.alcohol_open_time and hours.alcohol_close_time:
        if current_time < hours.alcohol_open_time:
            return {
                "can_sell": False,
                "reason": "Before alcohol sales hours",
                "starts_at": hours.alcohol_open_time
            }
        if current_time > hours.alcohol_close_time:
            return {
                "can_sell": False,
                "reason": "After alcohol sales hours",
                "ended_at": hours.alcohol_close_time
            }
    
    return {"can_sell": True}
