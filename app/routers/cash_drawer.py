# Cash Drawer Router - FR-032
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import json

from app.database import get_db
from app.models.cash_drawer import CashDrawer, CashMovement, SafeDrop

router = APIRouter(prefix="/cash-drawer", tags=["cash-drawer"])


class DrawerOpen(BaseModel):
    employee_id: int
    opening_amount: float
    register_number: int = 1


class DrawerClose(BaseModel):
    actual_amount: float
    denomination_breakdown: Optional[dict] = None
    notes: Optional[str] = None


class CashMovementCreate(BaseModel):
    movement_type: str
    amount: float
    performed_by: int
    authorized_by: Optional[int] = None
    reason: Optional[str] = None
    reference: Optional[str] = None


@router.post("/open")
def open_drawer(data: DrawerOpen, db: Session = Depends(get_db)):
    """Open a cash drawer session"""
    # Check for existing open drawer on this register
    existing = db.query(CashDrawer).filter(
        CashDrawer.register_number == data.register_number,
        CashDrawer.status == "open"
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Register {data.register_number} already has an open drawer")
    
    drawer = CashDrawer(
        employee_id=data.employee_id,
        register_number=data.register_number,
        opening_amount=data.opening_amount,
        status="open"
    )
    db.add(drawer)
    db.commit()
    db.refresh(drawer)
    
    return drawer


@router.get("/current")
def get_current_drawer(register_number: int = 1, db: Session = Depends(get_db)):
    """Get current open drawer for a register"""
    drawer = db.query(CashDrawer).filter(
        CashDrawer.register_number == register_number,
        CashDrawer.status == "open"
    ).first()
    
    if not drawer:
        raise HTTPException(status_code=404, detail="No open drawer found")
    
    # Calculate expected amount
    movements = db.query(CashMovement).filter(
        CashMovement.drawer_id == drawer.id
    ).all()
    
    cash_in = drawer.opening_amount
    for m in movements:
        if m.movement_type in ["paid_in", "pickup"]:
            cash_in += m.amount
        elif m.movement_type in ["drop", "paid_out"]:
            cash_in -= m.amount
    
    return {
        "drawer": drawer,
        "expected_amount": cash_in,
        "movements_count": len(movements)
    }


@router.post("/{drawer_id}/close")
def close_drawer(drawer_id: int, data: DrawerClose, db: Session = Depends(get_db)):
    """Close a cash drawer session"""
    drawer = db.query(CashDrawer).filter(CashDrawer.id == drawer_id).first()
    if not drawer:
        raise HTTPException(status_code=404, detail="Drawer not found")
    
    if drawer.status != "open":
        raise HTTPException(status_code=400, detail="Drawer is not open")
    
    # Calculate expected
    movements = db.query(CashMovement).filter(CashMovement.drawer_id == drawer_id).all()
    expected = drawer.opening_amount
    for m in movements:
        if m.movement_type in ["paid_in", "pickup"]:
            expected += m.amount
        elif m.movement_type in ["drop", "paid_out"]:
            expected -= m.amount
    
    drawer.closed_at = datetime.utcnow()
    drawer.expected_amount = expected
    drawer.actual_amount = data.actual_amount
    drawer.variance = data.actual_amount - expected
    drawer.status = "closed"
    drawer.notes = data.notes
    
    if data.denomination_breakdown:
        drawer.denomination_breakdown = json.dumps(data.denomination_breakdown)
    
    db.commit()
    db.refresh(drawer)
    
    return {
        "drawer": drawer,
        "variance": drawer.variance,
        "status": "over" if drawer.variance > 0 else "short" if drawer.variance < 0 else "balanced"
    }


@router.post("/{drawer_id}/movement")
def record_movement(drawer_id: int, movement: CashMovementCreate, db: Session = Depends(get_db)):
    """Record a cash movement"""
    drawer = db.query(CashDrawer).filter(CashDrawer.id == drawer_id).first()
    if not drawer:
        raise HTTPException(status_code=404, detail="Drawer not found")
    
    if drawer.status != "open":
        raise HTTPException(status_code=400, detail="Drawer is not open")
    
    db_movement = CashMovement(
        drawer_id=drawer_id,
        **movement.dict()
    )
    db.add(db_movement)
    db.commit()
    db.refresh(db_movement)
    
    return db_movement


@router.post("/{drawer_id}/safe-drop")
def record_safe_drop(
    drawer_id: int,
    amount: float,
    dropped_by: int,
    drop_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Record a safe drop"""
    drawer = db.query(CashDrawer).filter(CashDrawer.id == drawer_id).first()
    if not drawer:
        raise HTTPException(status_code=404, detail="Drawer not found")
    
    drop = SafeDrop(
        drawer_id=drawer_id,
        amount=amount,
        dropped_by=dropped_by,
        drop_number=drop_number
    )
    db.add(drop)
    
    # Also record as movement
    movement = CashMovement(
        drawer_id=drawer_id,
        movement_type="drop",
        amount=amount,
        performed_by=dropped_by,
        reference=drop_number
    )
    db.add(movement)
    
    db.commit()
    db.refresh(drop)
    
    return drop


@router.get("/history")
def get_drawer_history(
    days: int = 7,
    register_number: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get drawer history"""
    query = db.query(CashDrawer).filter(CashDrawer.status == "closed")
    
    if register_number:
        query = query.filter(CashDrawer.register_number == register_number)
    
    drawers = query.order_by(desc(CashDrawer.closed_at)).limit(50).all()
    
    total_variance = sum(d.variance or 0 for d in drawers)
    
    return {
        "drawers": drawers,
        "total_variance": total_variance,
        "sessions_count": len(drawers)
    }


@router.get("/variance-report")
def variance_report(db: Session = Depends(get_db)):
    """Get variance report by employee"""
    from sqlalchemy import func
    
    results = db.query(
        CashDrawer.employee_id,
        func.count(CashDrawer.id).label("sessions"),
        func.sum(CashDrawer.variance).label("total_variance"),
        func.avg(CashDrawer.variance).label("avg_variance")
    ).filter(
        CashDrawer.status == "closed"
    ).group_by(CashDrawer.employee_id).all()
    
    return {
        "by_employee": [
            {
                "employee_id": r.employee_id,
                "sessions": r.sessions,
                "total_variance": float(r.total_variance or 0),
                "avg_variance": float(r.avg_variance or 0)
            }
            for r in results
        ]
    }
