from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import Shift, Sale

router = APIRouter(prefix="/shifts", tags=["shifts"])


class ShiftStart(BaseModel):
    cashier_name: str
    opening_cash: float = 200.0


class ShiftEnd(BaseModel):
    closing_cash: float
    notes: Optional[str] = None


@router.get("/current")
def get_current_shift(db: Session = Depends(get_db)):
    """Get the currently active shift"""
    shift = db.query(Shift).filter(Shift.is_active == True).first()
    
    if not shift:
        return {"active": False, "message": "No active shift"}
    
    # Calculate current stats
    sales_during_shift = db.query(Sale).filter(
        Sale.created_at >= shift.start_time,
        Sale.payment_status == "completed"
    ).all()
    
    total_revenue = sum(s.total for s in sales_during_shift)
    cash_sales = sum(s.total for s in sales_during_shift if s.payment_method == "cash")
    card_sales = sum(s.total for s in sales_during_shift if s.payment_method == "card")
    
    duration = datetime.utcnow() - shift.start_time
    hours = duration.total_seconds() / 3600
    
    return {
        "active": True,
        "shift_id": shift.id,
        "cashier_name": shift.cashier_name,
        "start_time": shift.start_time,
        "duration_hours": round(hours, 2),
        "opening_cash": shift.opening_cash,
        "current_stats": {
            "total_sales": len(sales_during_shift),
            "total_revenue": round(total_revenue, 2),
            "cash_sales": round(cash_sales, 2),
            "card_sales": round(card_sales, 2),
            "expected_drawer": round(shift.opening_cash + cash_sales, 2)
        }
    }


@router.post("/start")
def start_shift(shift_data: ShiftStart, db: Session = Depends(get_db)):
    """Start a new shift"""
    # Check if there's already an active shift
    existing = db.query(Shift).filter(Shift.is_active == True).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Shift already active for {existing.cashier_name}"
        )
    
    shift = Shift(
        cashier_name=shift_data.cashier_name,
        opening_cash=shift_data.opening_cash
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    
    return {
        "shift_id": shift.id,
        "cashier_name": shift.cashier_name,
        "start_time": shift.start_time,
        "opening_cash": shift.opening_cash,
        "message": "Shift started successfully"
    }


@router.post("/end")
def end_shift(shift_data: ShiftEnd, db: Session = Depends(get_db)):
    """End the current shift"""
    shift = db.query(Shift).filter(Shift.is_active == True).first()
    
    if not shift:
        raise HTTPException(status_code=400, detail="No active shift to end")
    
    # Calculate final stats
    sales_during_shift = db.query(Sale).filter(
        Sale.created_at >= shift.start_time,
        Sale.payment_status == "completed"
    ).all()
    
    total_revenue = sum(s.total for s in sales_during_shift)
    cash_sales = sum(s.total for s in sales_during_shift if s.payment_method == "cash")
    card_sales = sum(s.total for s in sales_during_shift if s.payment_method == "card")
    
    expected_cash = shift.opening_cash + cash_sales
    cash_variance = shift_data.closing_cash - expected_cash
    
    # Update shift record
    shift.end_time = datetime.utcnow()
    shift.is_active = False
    shift.closing_cash = shift_data.closing_cash
    shift.expected_cash = expected_cash
    shift.cash_variance = cash_variance
    shift.total_sales = len(sales_during_shift)
    shift.total_revenue = total_revenue
    shift.total_cash_sales = cash_sales
    shift.total_card_sales = card_sales
    shift.notes = shift_data.notes
    
    db.commit()
    
    duration = shift.end_time - shift.start_time
    hours = duration.total_seconds() / 3600
    
    return {
        "shift_id": shift.id,
        "cashier_name": shift.cashier_name,
        "duration_hours": round(hours, 2),
        "summary": {
            "total_sales": len(sales_during_shift),
            "total_revenue": round(total_revenue, 2),
            "cash_sales": round(cash_sales, 2),
            "card_sales": round(card_sales, 2)
        },
        "cash_reconciliation": {
            "opening_cash": shift.opening_cash,
            "expected_cash": round(expected_cash, 2),
            "closing_cash": shift_data.closing_cash,
            "variance": round(cash_variance, 2),
            "status": "OK" if abs(cash_variance) < 1 else ("OVER" if cash_variance > 0 else "SHORT")
        },
        "message": "Shift ended successfully"
    }


@router.get("/history")
def get_shift_history(
    days: int = 7,
    cashier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get shift history"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Shift).filter(
        Shift.start_time >= start_date,
        Shift.is_active == False
    )
    
    if cashier:
        query = query.filter(Shift.cashier_name.ilike(f"%{cashier}%"))
    
    shifts = query.order_by(Shift.start_time.desc()).all()
    
    return {
        "period_days": days,
        "total_shifts": len(shifts),
        "shifts": [
            {
                "id": s.id,
                "cashier": s.cashier_name,
                "date": s.start_time.strftime("%Y-%m-%d"),
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M") if s.end_time else None,
                "duration_hours": round((s.end_time - s.start_time).total_seconds() / 3600, 2) if s.end_time else None,
                "sales_count": s.total_sales,
                "revenue": s.total_revenue,
                "cash_variance": s.cash_variance
            }
            for s in shifts
        ]
    }


@router.get("/{shift_id}")
def get_shift_details(shift_id: int, db: Session = Depends(get_db)):
    """Get details for a specific shift"""
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Get sales from this shift
    sales = db.query(Sale).filter(
        Sale.created_at >= shift.start_time,
        Sale.created_at <= (shift.end_time or datetime.utcnow()),
        Sale.payment_status == "completed"
    ).all()
    
    return {
        "shift": {
            "id": shift.id,
            "cashier": shift.cashier_name,
            "start_time": shift.start_time,
            "end_time": shift.end_time,
            "is_active": shift.is_active,
            "opening_cash": shift.opening_cash,
            "closing_cash": shift.closing_cash,
            "cash_variance": shift.cash_variance,
            "notes": shift.notes
        },
        "sales_summary": {
            "total_count": len(sales),
            "total_revenue": round(sum(s.total for s in sales), 2),
            "by_payment": {
                "cash": round(sum(s.total for s in sales if s.payment_method == "cash"), 2),
                "card": round(sum(s.total for s in sales if s.payment_method == "card"), 2)
            }
        },
        "sales": [
            {
                "id": s.id,
                "total": s.total,
                "payment_method": s.payment_method,
                "time": s.created_at.strftime("%H:%M")
            }
            for s in sales
        ]
    }
