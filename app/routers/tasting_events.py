# Tasting Events Router - FR-027
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.tasting_event import TastingEvent, TastingEventAttendee, SpiritsFlight

router = APIRouter(prefix="/tasting-events", tags=["tasting-events"])


class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str = "tasting"
    category: Optional[str] = None
    event_date: datetime
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: int = 90
    max_attendees: int = 20
    ticket_price: float = 0.0
    member_price: Optional[float] = None
    featured_products: Optional[str] = None
    host_employee_id: Optional[int] = None
    vendor_rep: Optional[str] = None


class AttendeeRegister(BaseModel):
    customer_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    ticket_type: str = "standard"


class FlightCreate(BaseModel):
    name: str
    description: Optional[str] = None
    flight_type: str = "whiskey"
    product_ids: str
    pour_size_oz: float = 0.5
    price: float
    member_price: Optional[float] = None


# Event endpoints
@router.post("/events")
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new tasting event"""
    db_event = TastingEvent(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.get("/events")
def list_events(
    upcoming: bool = True,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List tasting events"""
    query = db.query(TastingEvent)
    
    if upcoming:
        query = query.filter(TastingEvent.event_date >= datetime.now())
    if category:
        query = query.filter(TastingEvent.category == category)
    if status:
        query = query.filter(TastingEvent.status == status)
    
    return query.order_by(TastingEvent.event_date).all()


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get event details"""
    event = db.query(TastingEvent).filter(TastingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    attendees = db.query(TastingEventAttendee).filter(
        TastingEventAttendee.event_id == event_id
    ).all()
    
    return {
        "event": event,
        "attendees": attendees,
        "spots_remaining": event.max_attendees - event.current_attendees
    }


@router.post("/events/{event_id}/register")
def register_attendee(event_id: int, attendee: AttendeeRegister, db: Session = Depends(get_db)):
    """Register for an event"""
    event = db.query(TastingEvent).filter(TastingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.current_attendees >= event.max_attendees:
        raise HTTPException(status_code=400, detail="Event is full")
    
    # Determine price
    price = event.ticket_price
    if attendee.ticket_type == "member" and event.member_price:
        price = event.member_price
    
    db_attendee = TastingEventAttendee(
        event_id=event_id,
        customer_id=attendee.customer_id,
        guest_name=attendee.guest_name,
        guest_email=attendee.guest_email,
        guest_phone=attendee.guest_phone,
        ticket_type=attendee.ticket_type,
        amount_paid=price
    )
    db.add(db_attendee)
    
    event.current_attendees += 1
    db.commit()
    db.refresh(db_attendee)
    
    return {
        "registration": db_attendee,
        "ticket_price": price,
        "spots_remaining": event.max_attendees - event.current_attendees
    }


@router.post("/events/{event_id}/check-in/{attendee_id}")
def check_in_attendee(event_id: int, attendee_id: int, db: Session = Depends(get_db)):
    """Check in an attendee"""
    attendee = db.query(TastingEventAttendee).filter(
        TastingEventAttendee.id == attendee_id,
        TastingEventAttendee.event_id == event_id
    ).first()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    attendee.checked_in = True
    attendee.checked_in_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Checked in successfully", "attendee": attendee}


@router.patch("/events/{event_id}/status")
def update_event_status(event_id: int, status: str, db: Session = Depends(get_db)):
    """Update event status"""
    event = db.query(TastingEvent).filter(TastingEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.status = status
    db.commit()
    return {"message": f"Event status updated to {status}"}


# Spirits Flights endpoints
@router.post("/flights")
def create_flight(flight: FlightCreate, db: Session = Depends(get_db)):
    """Create a spirits flight"""
    db_flight = SpiritsFlight(**flight.dict(), is_active=True)
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    return db_flight


@router.get("/flights")
def list_flights(
    flight_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List available spirits flights"""
    query = db.query(SpiritsFlight)
    
    if active_only:
        query = query.filter(SpiritsFlight.is_active == True)
    if flight_type:
        query = query.filter(SpiritsFlight.flight_type == flight_type)
    
    return query.all()


@router.get("/flights/{flight_id}")
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    """Get flight details"""
    flight = db.query(SpiritsFlight).filter(SpiritsFlight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/calendar")
def get_event_calendar(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get events calendar view"""
    now = datetime.now()
    target_month = month or now.month
    target_year = year or now.year
    
    events = db.query(TastingEvent).filter(
        TastingEvent.status.in_(["scheduled", "in_progress"])
    ).order_by(TastingEvent.event_date).all()
    
    return {
        "month": target_month,
        "year": target_year,
        "events": [
            {
                "id": e.id,
                "name": e.name,
                "date": e.event_date.isoformat(),
                "category": e.category,
                "spots_remaining": e.max_attendees - e.current_attendees,
                "ticket_price": e.ticket_price
            }
            for e in events
        ]
    }
