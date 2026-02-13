from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import AgeVerification, Customer, Sale

router = APIRouter(prefix="/age-verification", tags=["age-verification"])

MINIMUM_AGE = 21


class VerificationCreate(BaseModel):
    sale_id: Optional[int] = None
    customer_id: Optional[int] = None
    verification_method: str = "visual"
    id_type: Optional[str] = None
    id_number_last4: Optional[str] = None
    date_of_birth: Optional[date] = None


def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


@router.post("/verify")
def verify_age(verification: VerificationCreate, db: Session = Depends(get_db)):
    """Record an age verification"""
    age = None
    verified = True
    declined_reason = None
    
    if verification.date_of_birth:
        age = calculate_age(verification.date_of_birth)
        if age < MINIMUM_AGE:
            verified = False
            declined_reason = f"Customer is {age} years old, minimum age is {MINIMUM_AGE}"
    
    record = AgeVerification(
        sale_id=verification.sale_id,
        customer_id=verification.customer_id,
        verification_method=verification.verification_method,
        id_type=verification.id_type,
        id_number_last4=verification.id_number_last4,
        date_of_birth=datetime.combine(verification.date_of_birth, datetime.min.time()) if verification.date_of_birth else None,
        age_at_verification=age,
        verified=verified,
        declined_reason=declined_reason
    )
    
    db.add(record)
    
    # Update customer's ID verified status
    if verification.customer_id and verified:
        customer = db.query(Customer).filter(Customer.id == verification.customer_id).first()
        if customer:
            customer.id_verified = True
            customer.id_verified_at = datetime.utcnow()
            if verification.date_of_birth:
                customer.date_of_birth = verification.date_of_birth
    
    db.commit()
    db.refresh(record)
    
    return {
        "verification_id": record.id,
        "verified": verified,
        "age": age,
        "declined_reason": declined_reason,
        "message": "Age verified successfully" if verified else "Age verification failed"
    }


@router.get("/check/{customer_id}")
def check_customer_verification(customer_id: int, db: Session = Depends(get_db)):
    """Check if customer has been previously verified"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get most recent verification
    last_verification = db.query(AgeVerification)\
        .filter(AgeVerification.customer_id == customer_id)\
        .order_by(AgeVerification.verified_at.desc())\
        .first()
    
    return {
        "customer_id": customer_id,
        "name": customer.name,
        "is_verified": customer.id_verified,
        "verified_at": customer.id_verified_at,
        "date_of_birth": customer.date_of_birth,
        "current_age": calculate_age(customer.date_of_birth) if customer.date_of_birth else None,
        "last_verification": {
            "id": last_verification.id,
            "method": last_verification.verification_method,
            "verified_at": last_verification.verified_at
        } if last_verification else None
    }


@router.get("/history")
def get_verification_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent age verification records (for compliance)"""
    verifications = db.query(AgeVerification)\
        .order_by(AgeVerification.verified_at.desc())\
        .limit(limit)\
        .all()
    
    return {
        "count": len(verifications),
        "verifications": [
            {
                "id": v.id,
                "sale_id": v.sale_id,
                "customer_id": v.customer_id,
                "method": v.verification_method,
                "id_type": v.id_type,
                "age": v.age_at_verification,
                "verified": v.verified,
                "declined_reason": v.declined_reason,
                "verified_at": v.verified_at
            }
            for v in verifications
        ]
    }


@router.get("/declined")
def get_declined_verifications(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get declined verifications for compliance reporting"""
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    declined = db.query(AgeVerification)\
        .filter(
            AgeVerification.verified == False,
            AgeVerification.verified_at >= start_date
        )\
        .order_by(AgeVerification.verified_at.desc())\
        .all()
    
    return {
        "period_days": days,
        "declined_count": len(declined),
        "records": [
            {
                "id": v.id,
                "age": v.age_at_verification,
                "reason": v.declined_reason,
                "verified_at": v.verified_at
            }
            for v in declined
        ]
    }


@router.post("/quick-verify")
def quick_verify(
    birth_year: int,
    birth_month: int = 1,
    birth_day: int = 1,
    db: Session = Depends(get_db)
):
    """Quick age check without full verification record"""
    try:
        dob = date(birth_year, birth_month, birth_day)
        age = calculate_age(dob)
        
        return {
            "date_of_birth": dob.isoformat(),
            "age": age,
            "is_legal_age": age >= MINIMUM_AGE,
            "minimum_age": MINIMUM_AGE
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date: {str(e)}")
