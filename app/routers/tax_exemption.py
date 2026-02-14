# Tax Exemption Router - FR-033
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.tax_exemption import TaxExemptCustomer, TaxExemptSale

router = APIRouter(prefix="/tax-exemption", tags=["tax-exemption"])


class ExemptionCreate(BaseModel):
    customer_id: int
    exemption_type: str
    certificate_number: str
    issuing_state: Optional[str] = None
    exempt_categories: Optional[str] = None
    effective_date: datetime
    expiration_date: Optional[datetime] = None


@router.post("/customers")
def create_exemption(exemption: ExemptionCreate, db: Session = Depends(get_db)):
    """Register a tax exempt customer"""
    db_exemption = TaxExemptCustomer(**exemption.dict(), is_active=True)
    db.add(db_exemption)
    db.commit()
    db.refresh(db_exemption)
    return db_exemption


@router.get("/customers")
def list_exempt_customers(
    active_only: bool = True,
    exemption_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List tax exempt customers"""
    query = db.query(TaxExemptCustomer)
    if active_only:
        query = query.filter(TaxExemptCustomer.is_active == True)
    if exemption_type:
        query = query.filter(TaxExemptCustomer.exemption_type == exemption_type)
    return query.all()


@router.get("/customers/{customer_id}")
def get_customer_exemption(customer_id: int, db: Session = Depends(get_db)):
    """Get customer's tax exemption status"""
    exemption = db.query(TaxExemptCustomer).filter(
        TaxExemptCustomer.customer_id == customer_id,
        TaxExemptCustomer.is_active == True
    ).first()
    
    if not exemption:
        return {"exempt": False}
    
    # Check if expired
    if exemption.expiration_date and exemption.expiration_date < datetime.utcnow():
        return {"exempt": False, "reason": "Certificate expired"}
    
    return {
        "exempt": True,
        "exemption": exemption
    }


@router.post("/customers/{exemption_id}/verify")
def verify_exemption(exemption_id: int, employee_id: int, db: Session = Depends(get_db)):
    """Mark exemption certificate as verified"""
    exemption = db.query(TaxExemptCustomer).filter(TaxExemptCustomer.id == exemption_id).first()
    if not exemption:
        raise HTTPException(status_code=404, detail="Exemption not found")
    
    exemption.certificate_on_file = True
    exemption.verified_by = employee_id
    exemption.verified_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Certificate verified"}


@router.post("/sales")
def record_exempt_sale(
    sale_id: int,
    exemption_id: int,
    tax_exempted: float,
    db: Session = Depends(get_db)
):
    """Record a tax exempt sale"""
    exemption = db.query(TaxExemptCustomer).filter(TaxExemptCustomer.id == exemption_id).first()
    if not exemption:
        raise HTTPException(status_code=404, detail="Exemption not found")
    
    exempt_sale = TaxExemptSale(
        sale_id=sale_id,
        exemption_id=exemption_id,
        tax_exempted=tax_exempted,
        exemption_type=exemption.exemption_type,
        certificate_number=exemption.certificate_number
    )
    db.add(exempt_sale)
    db.commit()
    db.refresh(exempt_sale)
    
    return exempt_sale


@router.get("/report")
def exemption_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get tax exemption report"""
    query = db.query(TaxExemptSale)
    
    if start_date:
        query = query.filter(TaxExemptSale.created_at >= start_date)
    if end_date:
        query = query.filter(TaxExemptSale.created_at <= end_date)
    
    sales = query.all()
    
    total_exempted = sum(s.tax_exempted for s in sales)
    by_type = {}
    for s in sales:
        if s.exemption_type not in by_type:
            by_type[s.exemption_type] = 0
        by_type[s.exemption_type] += s.tax_exempted
    
    return {
        "total_exempted": total_exempted,
        "transaction_count": len(sales),
        "by_type": by_type
    }
