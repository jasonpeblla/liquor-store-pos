from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all customers"""
    return db.query(Customer).offset(skip).limit(limit).all()


@router.get("/search")
def search_customers(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search customers by name, phone, or email"""
    search_filter = or_(
        Customer.name.ilike(f"%{q}%"),
        Customer.phone.ilike(f"%{q}%"),
        Customer.email.ilike(f"%{q}%")
    )
    return db.query(Customer).filter(search_filter).limit(20).all()


@router.post("", response_model=CustomerResponse)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    # Check for duplicate phone
    if customer.phone:
        existing = db.query(Customer).filter(Customer.phone == customer.phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already registered")
    
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a specific customer"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/{customer_id}/verify-id")
def verify_customer_id(customer_id: int, db: Session = Depends(get_db)):
    """Mark customer's ID as verified"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.id_verified = True
    customer.id_verified_at = datetime.utcnow()
    db.commit()
    
    return {"message": "ID verified", "customer_id": customer_id}


@router.get("/{customer_id}/purchase-history")
def get_purchase_history(customer_id: int, db: Session = Depends(get_db)):
    """Get customer's purchase history"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer_id": customer_id,
        "name": customer.name,
        "total_spent": customer.total_spent,
        "loyalty_points": customer.loyalty_points,
        "sales": [
            {
                "id": sale.id,
                "total": sale.total,
                "created_at": sale.created_at,
                "items_count": len(sale.items)
            }
            for sale in customer.sales
        ]
    }
