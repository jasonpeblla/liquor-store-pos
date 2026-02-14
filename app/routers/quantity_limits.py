from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.quantity_limit import QuantityLimit, QuantityLimitViolation
from app.models.product import Product
from app.models.category import Category
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.customer import Customer

router = APIRouter(prefix="/quantity-limits", tags=["quantity-limits"])


# Schemas
class LimitCreate(BaseModel):
    name: str
    limit_type: str = "category"  # category, product, alcohol
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    per_transaction: Optional[int] = None
    per_day: Optional[int] = None
    per_week: Optional[int] = None
    action: str = "block"
    warning_message: Optional[str] = None
    id_required_above: Optional[int] = None
    state_code: Optional[str] = None


class LimitUpdate(BaseModel):
    name: Optional[str] = None
    per_transaction: Optional[int] = None
    per_day: Optional[int] = None
    per_week: Optional[int] = None
    action: Optional[str] = None
    warning_message: Optional[str] = None
    id_required_above: Optional[int] = None
    is_active: Optional[bool] = None


class LimitResponse(BaseModel):
    id: int
    name: str
    limit_type: str
    category_id: Optional[int]
    product_id: Optional[int]
    per_transaction: Optional[int]
    per_day: Optional[int]
    per_week: Optional[int]
    action: str
    warning_message: Optional[str]
    id_required_above: Optional[int]
    state_code: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CheckLimitRequest(BaseModel):
    customer_id: Optional[int] = None
    product_id: int
    quantity: int


class CheckLimitResponse(BaseModel):
    allowed: bool
    adjusted_quantity: Optional[int]
    warnings: List[str]
    requires_manager: bool
    requires_id: bool
    violations: List[dict]


# Routes
@router.get("", response_model=List[LimitResponse])
def list_limits(
    active_only: bool = True,
    limit_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all quantity limits"""
    query = db.query(QuantityLimit)
    
    if active_only:
        query = query.filter(QuantityLimit.is_active == True)
    
    if limit_type:
        query = query.filter(QuantityLimit.limit_type == limit_type)
    
    return query.all()


@router.get("/{limit_id}", response_model=LimitResponse)
def get_limit(limit_id: int, db: Session = Depends(get_db)):
    """Get a specific limit"""
    limit = db.query(QuantityLimit).filter(QuantityLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")
    return limit


@router.post("", response_model=LimitResponse)
def create_limit(data: LimitCreate, db: Session = Depends(get_db)):
    """Create a new quantity limit"""
    limit = QuantityLimit(**data.model_dump())
    db.add(limit)
    db.commit()
    db.refresh(limit)
    return limit


@router.patch("/{limit_id}", response_model=LimitResponse)
def update_limit(limit_id: int, data: LimitUpdate, db: Session = Depends(get_db)):
    """Update a quantity limit"""
    limit = db.query(QuantityLimit).filter(QuantityLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(limit, key, value)
    
    db.commit()
    db.refresh(limit)
    return limit


@router.delete("/{limit_id}")
def delete_limit(limit_id: int, db: Session = Depends(get_db)):
    """Deactivate a limit"""
    limit = db.query(QuantityLimit).filter(QuantityLimit.id == limit_id).first()
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")
    
    limit.is_active = False
    db.commit()
    return {"message": "Limit deactivated"}


@router.post("/check", response_model=CheckLimitResponse)
def check_limit(data: CheckLimitRequest, db: Session = Depends(get_db)):
    """Check if a purchase would violate any limits"""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    warnings = []
    violations = []
    requires_manager = False
    requires_id = False
    allowed = True
    adjusted_quantity = data.quantity
    
    # Get applicable limits
    limits = db.query(QuantityLimit).filter(
        QuantityLimit.is_active == True
    ).all()
    
    applicable_limits = []
    for limit in limits:
        if limit.limit_type == "product" and limit.product_id == data.product_id:
            applicable_limits.append(limit)
        elif limit.limit_type == "category" and limit.category_id == product.category_id:
            applicable_limits.append(limit)
        elif limit.limit_type == "alcohol" and product.requires_age_verification:
            applicable_limits.append(limit)
    
    # Get customer's purchase history
    customer_today = 0
    customer_week = 0
    
    if data.customer_id:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        
        # Today's purchases
        customer_today = db.query(func.coalesce(func.sum(SaleItem.quantity), 0)).join(
            Sale, SaleItem.sale_id == Sale.id
        ).filter(
            Sale.customer_id == data.customer_id,
            Sale.created_at >= today_start,
            SaleItem.product_id == data.product_id
        ).scalar() or 0
        
        # Week's purchases
        customer_week = db.query(func.coalesce(func.sum(SaleItem.quantity), 0)).join(
            Sale, SaleItem.sale_id == Sale.id
        ).filter(
            Sale.customer_id == data.customer_id,
            Sale.created_at >= week_start,
            SaleItem.product_id == data.product_id
        ).scalar() or 0
    
    # Check each applicable limit
    for limit in applicable_limits:
        # Check per-transaction limit
        if limit.per_transaction and data.quantity > limit.per_transaction:
            violations.append({
                "limit_id": limit.id,
                "limit_name": limit.name,
                "type": "per_transaction",
                "limit": limit.per_transaction,
                "requested": data.quantity
            })
            
            if limit.action == "block":
                allowed = False
                adjusted_quantity = min(adjusted_quantity, limit.per_transaction)
            elif limit.action == "warn":
                warnings.append(limit.warning_message or f"Exceeds transaction limit of {limit.per_transaction}")
            elif limit.action == "require_manager":
                requires_manager = True
                warnings.append("Manager approval required for this quantity")
        
        # Check daily limit
        if limit.per_day and data.customer_id:
            if customer_today + data.quantity > limit.per_day:
                remaining = max(0, limit.per_day - customer_today)
                violations.append({
                    "limit_id": limit.id,
                    "limit_name": limit.name,
                    "type": "per_day",
                    "limit": limit.per_day,
                    "already_purchased": customer_today,
                    "requested": data.quantity,
                    "remaining": remaining
                })
                
                if limit.action == "block":
                    allowed = False
                    adjusted_quantity = min(adjusted_quantity, remaining)
                elif limit.action == "warn":
                    warnings.append(limit.warning_message or f"Near daily limit. Only {remaining} more allowed today.")
                elif limit.action == "require_manager":
                    requires_manager = True
        
        # Check weekly limit
        if limit.per_week and data.customer_id:
            if customer_week + data.quantity > limit.per_week:
                remaining = max(0, limit.per_week - customer_week)
                violations.append({
                    "limit_id": limit.id,
                    "limit_name": limit.name,
                    "type": "per_week",
                    "limit": limit.per_week,
                    "already_purchased": customer_week,
                    "requested": data.quantity,
                    "remaining": remaining
                })
                
                if limit.action == "block":
                    allowed = False
                    adjusted_quantity = min(adjusted_quantity, remaining)
                elif limit.action == "warn":
                    warnings.append(limit.warning_message or f"Near weekly limit. Only {remaining} more allowed this week.")
        
        # Check ID requirement
        if limit.id_required_above and data.quantity > limit.id_required_above:
            requires_id = True
            warnings.append(f"ID verification required for quantities over {limit.id_required_above}")
    
    return CheckLimitResponse(
        allowed=allowed,
        adjusted_quantity=adjusted_quantity if adjusted_quantity < data.quantity else None,
        warnings=warnings,
        requires_manager=requires_manager,
        requires_id=requires_id,
        violations=violations
    )


@router.post("/override")
def manager_override(
    violation_id: Optional[int] = None,
    product_id: int = None,
    customer_id: Optional[int] = None,
    quantity: int = None,
    manager_id: int = None,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """Record a manager override for a quantity limit"""
    # Log the override
    violation = QuantityLimitViolation(
        limit_id=violation_id or 0,  # May not have specific limit
        customer_id=customer_id,
        product_id=product_id,
        requested_quantity=quantity,
        allowed_quantity=quantity,
        action_taken="manager_override",
        manager_id=manager_id,
        override_reason=reason
    )
    db.add(violation)
    db.commit()
    
    return {
        "message": "Override recorded",
        "override_id": violation.id,
        "quantity_approved": quantity
    }


@router.get("/violations")
def list_violations(
    days: int = 30,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List quantity limit violations"""
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(QuantityLimitViolation).filter(
        QuantityLimitViolation.created_at >= since
    )
    
    if customer_id:
        query = query.filter(QuantityLimitViolation.customer_id == customer_id)
    
    return query.order_by(QuantityLimitViolation.created_at.desc()).all()


@router.post("/setup-defaults")
def setup_default_limits(db: Session = Depends(get_db)):
    """Set up default quantity limits for a liquor store"""
    defaults = [
        {
            "name": "Spirits Per Transaction",
            "limit_type": "category",
            "category_id": 3,  # Spirits
            "per_transaction": 6,
            "action": "warn",
            "warning_message": "Large spirits purchase - verify customer intent"
        },
        {
            "name": "Spirits Daily Limit",
            "limit_type": "category",
            "category_id": 3,  # Spirits
            "per_day": 12,
            "action": "require_manager",
            "warning_message": "Customer approaching daily spirits limit"
        },
        {
            "name": "High-Value Spirits ID Check",
            "limit_type": "category",
            "category_id": 3,  # Spirits
            "id_required_above": 2,
            "action": "warn",
            "warning_message": "ID check recommended for bulk spirits purchase"
        }
    ]
    
    created = []
    for d in defaults:
        limit = QuantityLimit(**d)
        db.add(limit)
        db.flush()
        created.append(limit.id)
    
    db.commit()
    
    return {"message": f"Created {len(created)} default limits", "limit_ids": created}
