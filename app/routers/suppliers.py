from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.supplier import Supplier

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# Schemas
class SupplierCreate(BaseModel):
    name: str
    code: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    license_number: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str = "Net 30"
    minimum_order: float = 0.0
    delivery_days: Optional[str] = None
    lead_time_days: int = 3
    supplies_beer: bool = False
    supplies_wine: bool = False
    supplies_spirits: bool = False
    supplies_other: bool = False
    notes: Optional[str] = None
    is_preferred: bool = False


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    license_number: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    minimum_order: Optional[float] = None
    delivery_days: Optional[str] = None
    lead_time_days: Optional[int] = None
    supplies_beer: Optional[bool] = None
    supplies_wine: Optional[bool] = None
    supplies_spirits: Optional[bool] = None
    supplies_other: Optional[bool] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_preferred: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    contact_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    license_number: Optional[str]
    tax_id: Optional[str]
    payment_terms: str
    minimum_order: float
    delivery_days: Optional[str]
    lead_time_days: int
    supplies_beer: bool
    supplies_wine: bool
    supplies_spirits: bool
    supplies_other: bool
    notes: Optional[str]
    is_active: bool
    is_preferred: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Routes
@router.get("", response_model=List[SupplierResponse])
def list_suppliers(
    active_only: bool = True,
    category: Optional[str] = Query(None, description="Filter by category: beer, wine, spirits, other"),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all suppliers with optional filters"""
    query = db.query(Supplier)
    
    if active_only:
        query = query.filter(Supplier.is_active == True)
    
    if category:
        if category == "beer":
            query = query.filter(Supplier.supplies_beer == True)
        elif category == "wine":
            query = query.filter(Supplier.supplies_wine == True)
        elif category == "spirits":
            query = query.filter(Supplier.supplies_spirits == True)
        elif category == "other":
            query = query.filter(Supplier.supplies_other == True)
    
    if search:
        query = query.filter(
            or_(
                Supplier.name.ilike(f"%{search}%"),
                Supplier.code.ilike(f"%{search}%"),
                Supplier.contact_name.ilike(f"%{search}%")
            )
        )
    
    return query.order_by(Supplier.is_preferred.desc(), Supplier.name).all()


@router.get("/preferred", response_model=List[SupplierResponse])
def list_preferred_suppliers(db: Session = Depends(get_db)):
    """Get all preferred suppliers"""
    return db.query(Supplier).filter(
        Supplier.is_active == True,
        Supplier.is_preferred == True
    ).all()


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """Get a specific supplier by ID"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("", response_model=SupplierResponse)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    """Create a new supplier"""
    # Check for duplicate code
    if data.code:
        existing = db.query(Supplier).filter(Supplier.code == data.code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Supplier code already exists")
    
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db)):
    """Update a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    """Soft delete a supplier (deactivate)"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    supplier.is_active = False
    db.commit()
    return {"message": "Supplier deactivated", "id": supplier_id}


@router.post("/{supplier_id}/toggle-preferred")
def toggle_preferred(supplier_id: int, db: Session = Depends(get_db)):
    """Toggle preferred status for a supplier"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    supplier.is_preferred = not supplier.is_preferred
    db.commit()
    return {"message": f"Supplier {'marked as' if supplier.is_preferred else 'removed from'} preferred", "is_preferred": supplier.is_preferred}
