from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.reservation import Reservation
from app.models.product import Product
from app.models.customer import Customer

router = APIRouter(prefix="/reservations", tags=["reservations"])


# Schemas
class ReservationCreate(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    product_id: int
    quantity: int = 1
    requested_date: Optional[datetime] = None
    deposit_amount: float = 0.0
    notes: Optional[str] = None
    created_by: Optional[int] = None


class ReservationUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    quantity: Optional[int] = None
    requested_date: Optional[datetime] = None
    expected_date: Optional[datetime] = None
    pickup_by_date: Optional[datetime] = None
    deposit_amount: Optional[float] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class ReservationResponse(BaseModel):
    id: int
    reservation_number: str
    customer_id: Optional[int]
    customer_name: str
    customer_phone: str
    customer_email: Optional[str]
    product_id: int
    quantity: int
    unit_price: float
    total_value: float
    deposit_amount: float
    deposit_paid: bool
    status: str
    requested_date: Optional[datetime]
    expected_date: Optional[datetime]
    pickup_by_date: Optional[datetime]
    picked_up_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


def generate_reservation_number(db: Session) -> str:
    """Generate unique reservation number"""
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(Reservation).filter(
        Reservation.reservation_number.like(f"R-{today}%")
    ).count()
    return f"R-{today}-{count + 1:03d}"


# Routes
@router.get("", response_model=List[ReservationResponse])
def list_reservations(
    status: Optional[str] = None,
    customer_phone: Optional[str] = None,
    product_id: Optional[int] = None,
    days: int = Query(30, description="Reservations from last N days"),
    db: Session = Depends(get_db)
):
    """List reservations with filters"""
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(Reservation).filter(Reservation.created_at >= since)
    
    if status:
        query = query.filter(Reservation.status == status)
    
    if customer_phone:
        query = query.filter(Reservation.customer_phone.contains(customer_phone))
    
    if product_id:
        query = query.filter(Reservation.product_id == product_id)
    
    reservations = query.order_by(Reservation.created_at.desc()).all()
    
    return [
        {
            **r.__dict__,
            "total_value": r.quantity * r.unit_price
        }
        for r in reservations
    ]


@router.get("/pending")
def list_pending_reservations(db: Session = Depends(get_db)):
    """Get all pending and confirmed reservations"""
    reservations = db.query(Reservation).filter(
        Reservation.status.in_(["pending", "confirmed", "ready"])
    ).order_by(Reservation.requested_date).all()
    
    result = []
    for r in reservations:
        product = db.query(Product).filter(Product.id == r.product_id).first()
        result.append({
            "id": r.id,
            "reservation_number": r.reservation_number,
            "customer_name": r.customer_name,
            "customer_phone": r.customer_phone,
            "product_name": product.name if product else "Unknown",
            "quantity": r.quantity,
            "total_value": r.quantity * r.unit_price,
            "deposit_paid": r.deposit_paid,
            "status": r.status,
            "requested_date": r.requested_date,
            "pickup_by_date": r.pickup_by_date
        })
    
    return result


@router.get("/lookup/{phone}")
def lookup_by_phone(phone: str, db: Session = Depends(get_db)):
    """Look up reservations by phone number"""
    reservations = db.query(Reservation).filter(
        Reservation.customer_phone.contains(phone),
        Reservation.status.in_(["pending", "confirmed", "ready"])
    ).all()
    
    return [
        {
            "id": r.id,
            "reservation_number": r.reservation_number,
            "product_id": r.product_id,
            "quantity": r.quantity,
            "status": r.status,
            "deposit_paid": r.deposit_paid,
            "created_at": r.created_at
        }
        for r in reservations
    ]


@router.get("/{reservation_id}")
def get_reservation(reservation_id: int, db: Session = Depends(get_db)):
    """Get a specific reservation"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    product = db.query(Product).filter(Product.id == reservation.product_id).first()
    
    return {
        **reservation.__dict__,
        "product_name": product.name if product else "Unknown",
        "product_brand": product.brand if product else None,
        "total_value": reservation.quantity * reservation.unit_price,
        "balance_due": (reservation.quantity * reservation.unit_price) - reservation.deposit_amount if reservation.deposit_paid else reservation.quantity * reservation.unit_price
    }


@router.post("", response_model=ReservationResponse)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db)):
    """Create a new reservation"""
    # Verify product exists and get price
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    reservation = Reservation(
        reservation_number=generate_reservation_number(db),
        customer_id=data.customer_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        customer_email=data.customer_email,
        product_id=data.product_id,
        quantity=data.quantity,
        unit_price=product.price,
        requested_date=data.requested_date,
        deposit_amount=data.deposit_amount,
        notes=data.notes,
        created_by=data.created_by,
        status="pending"
    )
    
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    
    return {
        **reservation.__dict__,
        "total_value": reservation.quantity * reservation.unit_price
    }


@router.patch("/{reservation_id}")
def update_reservation(reservation_id: int, data: ReservationUpdate, db: Session = Depends(get_db)):
    """Update a reservation"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reservation, key, value)
    
    db.commit()
    db.refresh(reservation)
    return {"message": "Reservation updated", "id": reservation_id}


@router.post("/{reservation_id}/pay-deposit")
def pay_deposit(
    reservation_id: int,
    payment_method: str = "cash",
    db: Session = Depends(get_db)
):
    """Mark deposit as paid"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    if reservation.deposit_paid:
        raise HTTPException(status_code=400, detail="Deposit already paid")
    
    reservation.deposit_paid = True
    reservation.deposit_payment_method = payment_method
    reservation.status = "confirmed"
    db.commit()
    
    return {
        "message": "Deposit paid",
        "reservation_number": reservation.reservation_number,
        "deposit_amount": reservation.deposit_amount
    }


@router.post("/{reservation_id}/mark-ready")
def mark_ready(reservation_id: int, db: Session = Depends(get_db)):
    """Mark reservation as ready for pickup"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    reservation.status = "ready"
    db.commit()
    
    return {
        "message": "Reservation marked as ready",
        "customer_phone": reservation.customer_phone,
        "customer_name": reservation.customer_name
    }


@router.post("/{reservation_id}/pickup")
def complete_pickup(reservation_id: int, db: Session = Depends(get_db)):
    """Complete reservation pickup"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    if reservation.status == "picked_up":
        raise HTTPException(status_code=400, detail="Already picked up")
    
    # Update inventory
    product = db.query(Product).filter(Product.id == reservation.product_id).first()
    if product:
        product.stock_quantity -= reservation.quantity
    
    reservation.status = "picked_up"
    reservation.picked_up_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Pickup completed",
        "reservation_number": reservation.reservation_number,
        "balance_due": (reservation.quantity * reservation.unit_price) - (reservation.deposit_amount if reservation.deposit_paid else 0)
    }


@router.post("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    refund_deposit: bool = False,
    db: Session = Depends(get_db)
):
    """Cancel a reservation"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    if reservation.status == "picked_up":
        raise HTTPException(status_code=400, detail="Cannot cancel completed reservation")
    
    reservation.status = "cancelled"
    db.commit()
    
    return {
        "message": "Reservation cancelled",
        "refund_deposit": refund_deposit,
        "deposit_amount": reservation.deposit_amount if refund_deposit and reservation.deposit_paid else 0
    }


@router.get("/expiring/soon")
def get_expiring_reservations(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get reservations expiring soon"""
    cutoff = datetime.utcnow() + timedelta(days=days)
    
    reservations = db.query(Reservation).filter(
        Reservation.status.in_(["pending", "confirmed", "ready"]),
        Reservation.pickup_by_date != None,
        Reservation.pickup_by_date <= cutoff
    ).order_by(Reservation.pickup_by_date).all()
    
    return [
        {
            "id": r.id,
            "reservation_number": r.reservation_number,
            "customer_name": r.customer_name,
            "customer_phone": r.customer_phone,
            "pickup_by_date": r.pickup_by_date,
            "days_until_expiry": (r.pickup_by_date - datetime.utcnow()).days,
            "status": r.status
        }
        for r in reservations
    ]
