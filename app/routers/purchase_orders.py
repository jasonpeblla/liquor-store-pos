from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.supplier import Supplier
from app.models.product import Product

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


# Schemas
class POItemCreate(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    sku: Optional[str] = None
    quantity_ordered: int
    unit_cost: float


class POItemResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: str
    sku: Optional[str]
    quantity_ordered: int
    quantity_received: int
    unit_cost: float
    total_cost: float
    received_at: Optional[datetime]

    class Config:
        from_attributes = True


class POCreate(BaseModel):
    supplier_id: int
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    items: List[POItemCreate] = []


class POUpdate(BaseModel):
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    shipping: Optional[float] = None
    tax: Optional[float] = None


class POResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    status: str
    order_date: datetime
    expected_date: Optional[datetime]
    received_date: Optional[datetime]
    subtotal: float
    tax: float
    shipping: float
    total: float
    notes: Optional[str]
    internal_notes: Optional[str]
    items: List[POItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReceiveItemRequest(BaseModel):
    item_id: int
    quantity_received: int


def generate_po_number(db: Session) -> str:
    """Generate unique PO number"""
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_number.like(f"PO-{today}%")
    ).count()
    return f"PO-{today}-{count + 1:03d}"


def calculate_totals(po: PurchaseOrder) -> None:
    """Recalculate PO totals"""
    po.subtotal = sum(item.total_cost for item in po.items)
    po.total = po.subtotal + po.tax + po.shipping


# Routes
@router.get("", response_model=List[POResponse])
def list_purchase_orders(
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    days: int = Query(30, description="Orders from last N days"),
    db: Session = Depends(get_db)
):
    """List purchase orders with filters"""
    query = db.query(PurchaseOrder)
    
    if status:
        query = query.filter(PurchaseOrder.status == status)
    
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(PurchaseOrder.created_at >= since)
    
    return query.order_by(PurchaseOrder.created_at.desc()).all()


@router.get("/pending", response_model=List[POResponse])
def list_pending_orders(db: Session = Depends(get_db)):
    """Get orders awaiting receipt"""
    return db.query(PurchaseOrder).filter(
        PurchaseOrder.status.in_([POStatus.SUBMITTED, POStatus.CONFIRMED, POStatus.SHIPPED])
    ).order_by(PurchaseOrder.expected_date).all()


@router.get("/{po_id}", response_model=POResponse)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """Get a specific purchase order"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.post("", response_model=POResponse)
def create_purchase_order(data: POCreate, db: Session = Depends(get_db)):
    """Create a new purchase order"""
    # Verify supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Create PO
    po = PurchaseOrder(
        po_number=generate_po_number(db),
        supplier_id=data.supplier_id,
        expected_date=data.expected_date,
        notes=data.notes,
        internal_notes=data.internal_notes,
        status=POStatus.DRAFT
    )
    db.add(po)
    db.flush()
    
    # Add items
    for item_data in data.items:
        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            sku=item_data.sku,
            quantity_ordered=item_data.quantity_ordered,
            unit_cost=item_data.unit_cost,
            total_cost=item_data.quantity_ordered * item_data.unit_cost
        )
        db.add(item)
    
    db.flush()
    calculate_totals(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/{po_id}/items", response_model=POItemResponse)
def add_item_to_order(po_id: int, item: POItemCreate, db: Session = Depends(get_db)):
    """Add an item to an existing PO"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status not in [POStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Cannot modify submitted order")
    
    po_item = PurchaseOrderItem(
        purchase_order_id=po_id,
        product_id=item.product_id,
        product_name=item.product_name,
        sku=item.sku,
        quantity_ordered=item.quantity_ordered,
        unit_cost=item.unit_cost,
        total_cost=item.quantity_ordered * item.unit_cost
    )
    db.add(po_item)
    db.flush()
    
    calculate_totals(po)
    db.commit()
    db.refresh(po_item)
    return po_item


@router.patch("/{po_id}", response_model=POResponse)
def update_purchase_order(po_id: int, data: POUpdate, db: Session = Depends(get_db)):
    """Update a purchase order"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(po, key, value)
    
    calculate_totals(po)
    db.commit()
    db.refresh(po)
    return po


@router.post("/{po_id}/submit")
def submit_order(po_id: int, db: Session = Depends(get_db)):
    """Submit PO to supplier"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status != POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Order already submitted")
    
    if not po.items:
        raise HTTPException(status_code=400, detail="Cannot submit empty order")
    
    po.status = POStatus.SUBMITTED
    po.order_date = datetime.utcnow()
    db.commit()
    
    return {"message": "Order submitted", "po_number": po.po_number}


@router.post("/{po_id}/receive")
def receive_items(po_id: int, items: List[ReceiveItemRequest], db: Session = Depends(get_db)):
    """Receive items from a purchase order and update inventory"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status not in [POStatus.SUBMITTED, POStatus.CONFIRMED, POStatus.SHIPPED]:
        raise HTTPException(status_code=400, detail="Order not in receivable state")
    
    received_count = 0
    for receive_item in items:
        po_item = db.query(PurchaseOrderItem).filter(
            PurchaseOrderItem.id == receive_item.item_id,
            PurchaseOrderItem.purchase_order_id == po_id
        ).first()
        
        if not po_item:
            continue
        
        po_item.quantity_received += receive_item.quantity_received
        po_item.received_at = datetime.utcnow()
        
        # Update product inventory if linked
        if po_item.product_id:
            product = db.query(Product).filter(Product.id == po_item.product_id).first()
            if product:
                product.stock_quantity += receive_item.quantity_received
        
        received_count += receive_item.quantity_received
    
    # Check if fully received
    all_received = all(
        item.quantity_received >= item.quantity_ordered 
        for item in po.items
    )
    
    if all_received:
        po.status = POStatus.RECEIVED
        po.received_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Received {received_count} items",
        "fully_received": all_received,
        "status": po.status
    }


@router.post("/{po_id}/cancel")
def cancel_order(po_id: int, db: Session = Depends(get_db)):
    """Cancel a purchase order"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Cannot cancel received order")
    
    po.status = POStatus.CANCELLED
    db.commit()
    
    return {"message": "Order cancelled", "po_number": po.po_number}


@router.get("/suggestions/reorder")
def get_reorder_suggestions(db: Session = Depends(get_db)):
    """Get products that need reordering based on low stock"""
    low_stock_products = db.query(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.is_active == True
    ).all()
    
    suggestions = []
    for product in low_stock_products:
        suggestions.append({
            "product_id": product.id,
            "product_name": product.name,
            "brand": product.brand,
            "current_stock": product.stock_quantity,
            "threshold": product.low_stock_threshold,
            "suggested_order": max(product.case_size or 12, product.low_stock_threshold * 2)
        })
    
    return suggestions
