# Delivery Router - FR-028
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.delivery import DeliveryOrder, DeliveryZone

router = APIRouter(prefix="/delivery", tags=["delivery"])


class DeliveryOrderCreate(BaseModel):
    sale_id: int
    customer_id: int
    order_type: str = "delivery"
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    delivery_instructions: Optional[str] = None
    requested_date: Optional[datetime] = None
    requested_time_slot: Optional[str] = None
    vehicle_description: Optional[str] = None
    parking_spot: Optional[str] = None
    delivery_fee: float = 0.0


class ZoneCreate(BaseModel):
    zone_name: str
    zip_codes: Optional[str] = None
    delivery_fee: float = 0.0
    minimum_order: float = 0.0
    free_delivery_threshold: Optional[float] = None
    available_days: str = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
    start_time: str = "10:00"
    end_time: str = "20:00"


# Order endpoints
@router.post("/orders")
def create_delivery_order(order: DeliveryOrderCreate, db: Session = Depends(get_db)):
    """Create a delivery/curbside order"""
    db_order = DeliveryOrder(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@router.get("/orders")
def list_delivery_orders(
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    driver_id: Optional[int] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List delivery orders"""
    query = db.query(DeliveryOrder)
    
    if status:
        query = query.filter(DeliveryOrder.status == status)
    if order_type:
        query = query.filter(DeliveryOrder.order_type == order_type)
    if driver_id:
        query = query.filter(DeliveryOrder.driver_employee_id == driver_id)
    
    return query.order_by(desc(DeliveryOrder.created_at)).all()


@router.get("/orders/{order_id}")
def get_delivery_order(order_id: int, db: Session = Depends(get_db)):
    """Get delivery order details"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    """Update delivery order status"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = status
    
    if status == "out_for_delivery":
        order.picked_up_at = datetime.utcnow()
    elif status == "delivered":
        order.delivered_at = datetime.utcnow()
    
    db.commit()
    return {"message": f"Order status updated to {status}"}


@router.post("/orders/{order_id}/assign")
def assign_driver(order_id: int, driver_id: int, db: Session = Depends(get_db)):
    """Assign driver to delivery"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.driver_employee_id = driver_id
    order.assigned_at = datetime.utcnow()
    order.status = "confirmed"
    db.commit()
    
    return {"message": f"Driver {driver_id} assigned to order {order_id}"}


@router.post("/orders/{order_id}/verify-age")
def verify_age_at_delivery(
    order_id: int,
    id_type: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Record age verification at delivery"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.age_verified_at_delivery = True
    order.id_type_verified = id_type
    order.verifier_notes = notes
    db.commit()
    
    return {"message": "Age verified at delivery"}


# Curbside endpoints
@router.get("/curbside/queue")
def get_curbside_queue(db: Session = Depends(get_db)):
    """Get current curbside pickup queue"""
    orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.order_type == "curbside",
        DeliveryOrder.status.in_(["pending", "confirmed", "preparing"])
    ).order_by(DeliveryOrder.requested_date).all()
    
    return {"queue": orders}


@router.post("/curbside/{order_id}/arrived")
def customer_arrived(order_id: int, parking_spot: Optional[str] = None, db: Session = Depends(get_db)):
    """Customer signals arrival for curbside pickup"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if parking_spot:
        order.parking_spot = parking_spot
    order.status = "customer_arrived"
    db.commit()
    
    return {"message": "Staff notified of arrival", "parking_spot": order.parking_spot}


# Zone management
@router.post("/zones")
def create_zone(zone: ZoneCreate, db: Session = Depends(get_db)):
    """Create a delivery zone"""
    db_zone = DeliveryZone(**zone.dict(), is_active=True)
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone


@router.get("/zones")
def list_zones(active_only: bool = True, db: Session = Depends(get_db)):
    """List delivery zones"""
    query = db.query(DeliveryZone)
    if active_only:
        query = query.filter(DeliveryZone.is_active == True)
    return query.all()


@router.get("/zones/check")
def check_delivery_availability(zip_code: str, db: Session = Depends(get_db)):
    """Check if delivery is available to a zip code"""
    zones = db.query(DeliveryZone).filter(
        DeliveryZone.is_active == True
    ).all()
    
    for zone in zones:
        if zone.zip_codes and zip_code in zone.zip_codes.split(","):
            return {
                "available": True,
                "zone": zone.zone_name,
                "delivery_fee": zone.delivery_fee,
                "minimum_order": zone.minimum_order,
                "free_delivery_threshold": zone.free_delivery_threshold
            }
    
    return {"available": False, "message": "Delivery not available to this area"}


@router.get("/dashboard")
def delivery_dashboard(db: Session = Depends(get_db)):
    """Get delivery operations dashboard"""
    pending = db.query(DeliveryOrder).filter(DeliveryOrder.status == "pending").count()
    out_for_delivery = db.query(DeliveryOrder).filter(DeliveryOrder.status == "out_for_delivery").count()
    curbside_waiting = db.query(DeliveryOrder).filter(
        DeliveryOrder.order_type == "curbside",
        DeliveryOrder.status == "customer_arrived"
    ).count()
    
    return {
        "pending_orders": pending,
        "out_for_delivery": out_for_delivery,
        "curbside_waiting": curbside_waiting
    }
