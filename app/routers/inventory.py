from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Product, Category

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/low-stock")
def get_low_stock_products(
    threshold_override: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get products with low stock levels"""
    query = db.query(Product).filter(Product.is_active == True)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    products = query.all()
    
    low_stock = []
    for product in products:
        threshold = threshold_override if threshold_override else product.low_stock_threshold
        if product.stock_quantity <= threshold:
            low_stock.append({
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "category": product.category.name if product.category else None,
                "stock_quantity": product.stock_quantity,
                "low_stock_threshold": product.low_stock_threshold,
                "needs_reorder": product.stock_quantity == 0
            })
    
    return {
        "count": len(low_stock),
        "products": sorted(low_stock, key=lambda x: x["stock_quantity"])
    }


@router.get("/out-of-stock")
def get_out_of_stock_products(db: Session = Depends(get_db)):
    """Get products that are completely out of stock"""
    products = db.query(Product)\
        .filter(Product.is_active == True)\
        .filter(Product.stock_quantity == 0)\
        .all()
    
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "brand": p.brand,
                "category": p.category.name if p.category else None
            }
            for p in products
        ]
    }


@router.get("/summary")
def get_inventory_summary(db: Session = Depends(get_db)):
    """Get inventory summary by category"""
    categories = db.query(Category).all()
    
    summary = []
    total_products = 0
    total_value = 0.0
    total_low_stock = 0
    total_out_of_stock = 0
    
    for category in categories:
        products = db.query(Product)\
            .filter(Product.category_id == category.id)\
            .filter(Product.is_active == True)\
            .all()
        
        cat_value = sum(p.price * p.stock_quantity for p in products)
        cat_low_stock = sum(1 for p in products if p.stock_quantity <= p.low_stock_threshold and p.stock_quantity > 0)
        cat_out_of_stock = sum(1 for p in products if p.stock_quantity == 0)
        
        summary.append({
            "category_id": category.id,
            "category_name": category.name,
            "product_count": len(products),
            "total_units": sum(p.stock_quantity for p in products),
            "inventory_value": round(cat_value, 2),
            "low_stock_count": cat_low_stock,
            "out_of_stock_count": cat_out_of_stock
        })
        
        total_products += len(products)
        total_value += cat_value
        total_low_stock += cat_low_stock
        total_out_of_stock += cat_out_of_stock
    
    return {
        "total_products": total_products,
        "total_inventory_value": round(total_value, 2),
        "total_low_stock": total_low_stock,
        "total_out_of_stock": total_out_of_stock,
        "by_category": summary
    }


@router.post("/bulk-update")
def bulk_update_inventory(
    updates: List[dict],
    db: Session = Depends(get_db)
):
    """Bulk update product inventory
    
    Expected format: [{"product_id": 1, "quantity": 100}, ...]
    """
    results = []
    
    for update in updates:
        product_id = update.get("product_id")
        quantity = update.get("quantity")
        
        if product_id is None or quantity is None:
            results.append({"product_id": product_id, "success": False, "error": "Missing required fields"})
            continue
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            results.append({"product_id": product_id, "success": False, "error": "Product not found"})
            continue
        
        product.stock_quantity = quantity
        results.append({
            "product_id": product_id,
            "name": product.name,
            "success": True,
            "new_quantity": quantity
        })
    
    db.commit()
    
    return {
        "updated": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results
    }
