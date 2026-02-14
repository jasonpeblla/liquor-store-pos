from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.bottle_deposit import BottleDepositConfig, BottleReturn, ProductDeposit
from app.models.product import Product
from app.models.customer import Customer

router = APIRouter(prefix="/bottle-deposits", tags=["bottle-deposits"])


# Schemas
class DepositConfigCreate(BaseModel):
    name: str
    container_type: str
    size_min_oz: Optional[float] = None
    size_max_oz: Optional[float] = None
    deposit_amount: float
    state_code: Optional[str] = None


class DepositConfigResponse(BaseModel):
    id: int
    name: str
    container_type: str
    size_min_oz: Optional[float]
    size_max_oz: Optional[float]
    deposit_amount: float
    is_active: bool
    state_code: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductDepositCreate(BaseModel):
    product_id: int
    container_type: str
    containers_per_unit: int = 1
    deposit_per_container: float


class ProductDepositResponse(BaseModel):
    id: int
    product_id: int
    container_type: str
    containers_per_unit: int
    deposit_per_container: float
    total_deposit: float

    class Config:
        from_attributes = True


class BottleReturnCreate(BaseModel):
    customer_id: Optional[int] = None
    container_type: str
    quantity: int
    deposit_per_unit: float
    refund_method: str = "cash"
    shift_id: Optional[int] = None
    notes: Optional[str] = None


class BottleReturnResponse(BaseModel):
    id: int
    customer_id: Optional[int]
    container_type: str
    quantity: int
    deposit_per_unit: float
    total_refund: float
    refund_method: str
    shift_id: Optional[int]
    processed: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Deposit Config Routes
@router.get("/config", response_model=List[DepositConfigResponse])
def list_deposit_configs(
    active_only: bool = True,
    state_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all deposit configurations"""
    query = db.query(BottleDepositConfig)
    
    if active_only:
        query = query.filter(BottleDepositConfig.is_active == True)
    
    if state_code:
        query = query.filter(
            (BottleDepositConfig.state_code == state_code) | 
            (BottleDepositConfig.state_code == None)
        )
    
    return query.all()


@router.post("/config", response_model=DepositConfigResponse)
def create_deposit_config(data: DepositConfigCreate, db: Session = Depends(get_db)):
    """Create a new deposit configuration"""
    config = BottleDepositConfig(**data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.delete("/config/{config_id}")
def delete_deposit_config(config_id: int, db: Session = Depends(get_db)):
    """Deactivate a deposit configuration"""
    config = db.query(BottleDepositConfig).filter(BottleDepositConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    config.is_active = False
    db.commit()
    return {"message": "Config deactivated"}


# Product Deposit Routes
@router.get("/products", response_model=List[ProductDepositResponse])
def list_product_deposits(db: Session = Depends(get_db)):
    """List all products with deposits"""
    deposits = db.query(ProductDeposit).all()
    result = []
    for d in deposits:
        result.append({
            "id": d.id,
            "product_id": d.product_id,
            "container_type": d.container_type,
            "containers_per_unit": d.containers_per_unit,
            "deposit_per_container": d.deposit_per_container,
            "total_deposit": d.containers_per_unit * d.deposit_per_container
        })
    return result


@router.post("/products", response_model=ProductDepositResponse)
def assign_product_deposit(data: ProductDepositCreate, db: Session = Depends(get_db)):
    """Assign deposit requirement to a product"""
    # Check product exists
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already assigned
    existing = db.query(ProductDeposit).filter(ProductDeposit.product_id == data.product_id).first()
    if existing:
        # Update existing
        existing.container_type = data.container_type
        existing.containers_per_unit = data.containers_per_unit
        existing.deposit_per_container = data.deposit_per_container
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "product_id": existing.product_id,
            "container_type": existing.container_type,
            "containers_per_unit": existing.containers_per_unit,
            "deposit_per_container": existing.deposit_per_container,
            "total_deposit": existing.containers_per_unit * existing.deposit_per_container
        }
    
    deposit = ProductDeposit(**data.model_dump())
    db.add(deposit)
    db.commit()
    db.refresh(deposit)
    return {
        "id": deposit.id,
        "product_id": deposit.product_id,
        "container_type": deposit.container_type,
        "containers_per_unit": deposit.containers_per_unit,
        "deposit_per_container": deposit.deposit_per_container,
        "total_deposit": deposit.containers_per_unit * deposit.deposit_per_container
    }


@router.get("/products/{product_id}")
def get_product_deposit(product_id: int, db: Session = Depends(get_db)):
    """Get deposit info for a specific product"""
    deposit = db.query(ProductDeposit).filter(ProductDeposit.product_id == product_id).first()
    if not deposit:
        return {"product_id": product_id, "has_deposit": False, "total_deposit": 0}
    
    return {
        "product_id": product_id,
        "has_deposit": True,
        "container_type": deposit.container_type,
        "containers_per_unit": deposit.containers_per_unit,
        "deposit_per_container": deposit.deposit_per_container,
        "total_deposit": deposit.containers_per_unit * deposit.deposit_per_container
    }


# Bottle Return Routes
@router.post("/returns", response_model=BottleReturnResponse)
def process_return(data: BottleReturnCreate, db: Session = Depends(get_db)):
    """Process a bottle return"""
    total_refund = data.quantity * data.deposit_per_unit
    
    return_record = BottleReturn(
        customer_id=data.customer_id,
        container_type=data.container_type,
        quantity=data.quantity,
        deposit_per_unit=data.deposit_per_unit,
        total_refund=total_refund,
        refund_method=data.refund_method,
        shift_id=data.shift_id,
        notes=data.notes
    )
    db.add(return_record)
    db.commit()
    db.refresh(return_record)
    return return_record


@router.get("/returns", response_model=List[BottleReturnResponse])
def list_returns(
    days: int = 7,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List bottle returns"""
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(BottleReturn).filter(BottleReturn.created_at >= since)
    
    if customer_id:
        query = query.filter(BottleReturn.customer_id == customer_id)
    
    return query.order_by(BottleReturn.created_at.desc()).all()


@router.get("/returns/summary")
def returns_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get summary of bottle returns"""
    query = db.query(BottleReturn)
    
    if start_date:
        query = query.filter(BottleReturn.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(BottleReturn.created_at <= datetime.combine(end_date, datetime.max.time()))
    
    returns = query.all()
    
    by_type = {}
    for r in returns:
        if r.container_type not in by_type:
            by_type[r.container_type] = {"count": 0, "refunded": 0}
        by_type[r.container_type]["count"] += r.quantity
        by_type[r.container_type]["refunded"] += r.total_refund
    
    return {
        "total_containers": sum(r.quantity for r in returns),
        "total_refunded": round(sum(r.total_refund for r in returns), 2),
        "by_container_type": by_type,
        "return_count": len(returns)
    }


@router.post("/calculate-cart-deposits")
def calculate_cart_deposits(
    items: List[dict],  # [{"product_id": 1, "quantity": 2}, ...]
    db: Session = Depends(get_db)
):
    """Calculate total deposits for a cart"""
    product_ids = [item["product_id"] for item in items]
    deposits = {d.product_id: d for d in db.query(ProductDeposit).filter(
        ProductDeposit.product_id.in_(product_ids)
    ).all()}
    
    total_deposit = 0
    breakdown = []
    
    for item in items:
        pid = item["product_id"]
        qty = item["quantity"]
        
        if pid in deposits:
            d = deposits[pid]
            item_deposit = d.containers_per_unit * d.deposit_per_container * qty
            total_deposit += item_deposit
            breakdown.append({
                "product_id": pid,
                "quantity": qty,
                "deposit_per_unit": d.containers_per_unit * d.deposit_per_container,
                "total": item_deposit
            })
    
    return {
        "total_deposit": round(total_deposit, 2),
        "breakdown": breakdown
    }
