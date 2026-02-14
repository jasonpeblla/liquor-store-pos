# Returns Router - FR-036
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.return_policy import ReturnPolicy, ProductReturn, Exchange
from app.models import Product

router = APIRouter(prefix="/returns", tags=["returns"])


class PolicyCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    return_days: int = 30
    exchange_days: int = 60
    requires_receipt: bool = True
    requires_unopened: bool = True
    restocking_fee_percent: float = 0
    refund_type: str = "original"


class ReturnCreate(BaseModel):
    original_sale_id: Optional[int] = None
    product_id: int
    customer_id: Optional[int] = None
    quantity: int
    unit_price: float
    return_reason: str
    condition: str = "unopened"
    refund_method: str = "original"


# Policy endpoints
@router.post("/policies")
def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    """Create return policy"""
    db_policy = ReturnPolicy(**policy.dict(), is_active=True)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


@router.get("/policies")
def list_policies(db: Session = Depends(get_db)):
    """List return policies"""
    return db.query(ReturnPolicy).filter(ReturnPolicy.is_active == True).all()


@router.get("/policies/{product_id}")
def get_product_policy(product_id: int, db: Session = Depends(get_db)):
    """Get return policy for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check category-specific policy
    policy = db.query(ReturnPolicy).filter(
        ReturnPolicy.category_id == product.category_id,
        ReturnPolicy.is_active == True
    ).first()
    
    if not policy:
        # Fall back to default policy
        policy = db.query(ReturnPolicy).filter(
            ReturnPolicy.category_id == None,
            ReturnPolicy.is_active == True
        ).first()
    
    return policy


# Return endpoints
@router.post("/")
def create_return(ret: ReturnCreate, db: Session = Depends(get_db)):
    """Initiate a product return"""
    product = db.query(Product).filter(Product.id == ret.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get policy
    policy = db.query(ReturnPolicy).filter(
        (ReturnPolicy.category_id == product.category_id) | (ReturnPolicy.category_id == None),
        ReturnPolicy.is_active == True
    ).first()
    
    # Calculate refund
    subtotal = ret.quantity * ret.unit_price
    restocking_fee = 0
    if policy and policy.restocking_fee_percent > 0:
        restocking_fee = subtotal * (policy.restocking_fee_percent / 100)
    
    refund_amount = subtotal - restocking_fee
    
    db_return = ProductReturn(
        **ret.dict(),
        refund_amount=refund_amount,
        restocking_fee=restocking_fee,
        status="pending"
    )
    db.add(db_return)
    db.commit()
    db.refresh(db_return)
    
    return {
        "return": db_return,
        "refund_amount": refund_amount,
        "restocking_fee": restocking_fee
    }


@router.get("/")
def list_returns(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List returns"""
    query = db.query(ProductReturn)
    if status:
        query = query.filter(ProductReturn.status == status)
    return query.order_by(desc(ProductReturn.created_at)).limit(limit).all()


@router.get("/{return_id}")
def get_return(return_id: int, db: Session = Depends(get_db)):
    """Get return details"""
    ret = db.query(ProductReturn).filter(ProductReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    return ret


@router.post("/{return_id}/approve")
def approve_return(return_id: int, employee_id: int, db: Session = Depends(get_db)):
    """Approve a return"""
    ret = db.query(ProductReturn).filter(ProductReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    
    ret.status = "approved"
    ret.approved_by = employee_id
    db.commit()
    
    return {"message": "Return approved", "refund_amount": ret.refund_amount}


@router.post("/{return_id}/complete")
def complete_return(return_id: int, db: Session = Depends(get_db)):
    """Complete the return and update inventory"""
    ret = db.query(ProductReturn).filter(ProductReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    
    if ret.status != "approved":
        raise HTTPException(status_code=400, detail="Return must be approved first")
    
    # Update inventory if condition allows resale
    if ret.condition == "unopened":
        product = db.query(Product).filter(Product.id == ret.product_id).first()
        if product:
            product.stock_quantity += ret.quantity
    
    ret.status = "completed"
    ret.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Return completed", "inventory_updated": ret.condition == "unopened"}


@router.post("/{return_id}/exchange")
def create_exchange(return_id: int, new_product_id: int, db: Session = Depends(get_db)):
    """Exchange returned product for another"""
    ret = db.query(ProductReturn).filter(ProductReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    
    new_product = db.query(Product).filter(Product.id == new_product_id).first()
    if not new_product:
        raise HTTPException(status_code=404, detail="New product not found")
    
    price_diff = (new_product.price * ret.quantity) - ret.refund_amount
    
    exchange = Exchange(
        return_id=return_id,
        new_product_id=new_product_id,
        price_difference=price_diff
    )
    db.add(exchange)
    
    ret.status = "completed"
    ret.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(exchange)
    
    return {
        "exchange": exchange,
        "price_difference": price_diff,
        "action": "customer_pays" if price_diff > 0 else "refund_difference" if price_diff < 0 else "even"
    }


@router.get("/report")
def returns_report(db: Session = Depends(get_db)):
    """Get returns report"""
    total_returns = db.query(func.count(ProductReturn.id)).filter(
        ProductReturn.status == "completed"
    ).scalar() or 0
    
    total_refunded = db.query(func.sum(ProductReturn.refund_amount)).filter(
        ProductReturn.status == "completed"
    ).scalar() or 0
    
    by_reason = db.query(
        ProductReturn.return_reason,
        func.count(ProductReturn.id)
    ).filter(
        ProductReturn.status == "completed"
    ).group_by(ProductReturn.return_reason).all()
    
    return {
        "total_returns": total_returns,
        "total_refunded": float(total_refunded),
        "by_reason": {r: c for r, c in by_reason}
    }
