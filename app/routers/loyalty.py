from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Customer, Sale

router = APIRouter(prefix="/loyalty", tags=["loyalty"])

# Loyalty program settings
POINTS_PER_DOLLAR = 1
POINTS_TO_DOLLAR_RATIO = 100  # 100 points = $1 redemption


@router.get("/settings")
def get_loyalty_settings():
    """Get loyalty program settings"""
    return {
        "points_per_dollar": POINTS_PER_DOLLAR,
        "points_to_dollar_ratio": POINTS_TO_DOLLAR_RATIO,
        "dollar_value_per_100_points": 1.0
    }


@router.get("/customer/{customer_id}")
def get_customer_loyalty(customer_id: int, db: Session = Depends(get_db)):
    """Get customer's loyalty status"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Calculate tier based on total spent
    total_spent = customer.total_spent
    tier = "Bronze"
    tier_benefits = "1 point per $1"
    
    if total_spent >= 5000:
        tier = "Platinum"
        tier_benefits = "2x points, exclusive discounts"
    elif total_spent >= 2000:
        tier = "Gold"
        tier_benefits = "1.5x points, birthday bonus"
    elif total_spent >= 500:
        tier = "Silver"
        tier_benefits = "1.25x points"
    
    # Calculate redeemable value
    redeemable_value = customer.loyalty_points / POINTS_TO_DOLLAR_RATIO
    
    return {
        "customer_id": customer_id,
        "name": customer.name,
        "current_points": customer.loyalty_points,
        "redeemable_value": round(redeemable_value, 2),
        "total_spent": round(customer.total_spent, 2),
        "tier": tier,
        "tier_benefits": tier_benefits,
        "points_to_next_redemption": max(0, POINTS_TO_DOLLAR_RATIO - (customer.loyalty_points % POINTS_TO_DOLLAR_RATIO))
    }


@router.post("/customer/{customer_id}/redeem")
def redeem_points(
    customer_id: int,
    points: int,
    db: Session = Depends(get_db)
):
    """Redeem loyalty points for store credit"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if points < POINTS_TO_DOLLAR_RATIO:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum {POINTS_TO_DOLLAR_RATIO} points required for redemption"
        )
    
    if points > customer.loyalty_points:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient points. Available: {customer.loyalty_points}"
        )
    
    # Calculate redemption value
    redeemable_points = (points // POINTS_TO_DOLLAR_RATIO) * POINTS_TO_DOLLAR_RATIO
    dollar_value = redeemable_points / POINTS_TO_DOLLAR_RATIO
    
    # Deduct points
    customer.loyalty_points -= redeemable_points
    db.commit()
    
    return {
        "success": True,
        "points_redeemed": redeemable_points,
        "dollar_value": dollar_value,
        "remaining_points": customer.loyalty_points
    }


@router.post("/customer/{customer_id}/add-points")
def add_bonus_points(
    customer_id: int,
    points: int,
    reason: str = "manual_bonus",
    db: Session = Depends(get_db)
):
    """Add bonus points to customer account"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.loyalty_points += points
    db.commit()
    
    return {
        "success": True,
        "points_added": points,
        "reason": reason,
        "new_balance": customer.loyalty_points
    }


@router.get("/leaderboard")
def get_loyalty_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """Get top customers by loyalty points"""
    customers = db.query(Customer)\
        .order_by(Customer.loyalty_points.desc())\
        .limit(limit)\
        .all()
    
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "customer_id": c.id,
                "name": c.name,
                "points": c.loyalty_points,
                "total_spent": round(c.total_spent, 2)
            }
            for i, c in enumerate(customers)
        ]
    }


@router.post("/lookup-by-phone")
def lookup_by_phone(phone: str, db: Session = Depends(get_db)):
    """Quick loyalty lookup by phone number"""
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    
    if not customer:
        return {
            "found": False,
            "phone": phone,
            "message": "No loyalty account found. Would you like to create one?"
        }
    
    return {
        "found": True,
        "customer_id": customer.id,
        "name": customer.name,
        "points": customer.loyalty_points,
        "redeemable_value": round(customer.loyalty_points / POINTS_TO_DOLLAR_RATIO, 2)
    }
