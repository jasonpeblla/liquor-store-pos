from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/quick-add", tags=["quick-add"])


@router.get("/favorites")
def get_favorite_products(limit: int = 8, db: Session = Depends(get_db)):
    """Get frequently sold products for quick add buttons"""
    products = db.query(Product)\
        .filter(Product.is_active == True, Product.stock_quantity > 0)\
        .order_by(Product.times_sold.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "brand": p.brand,
            "price": p.price,
            "category": p.category.name if p.category else None,
            "stock": p.stock_quantity,
            "requires_age": p.requires_age_verification
        }
        for p in products
    ]


@router.get("/by-category/{category_id}")
def get_quick_add_by_category(
    category_id: int,
    limit: int = 6,
    db: Session = Depends(get_db)
):
    """Get top products in a category for quick add"""
    products = db.query(Product)\
        .filter(
            Product.category_id == category_id,
            Product.is_active == True,
            Product.stock_quantity > 0
        )\
        .order_by(Product.times_sold.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "stock": p.stock_quantity
        }
        for p in products
    ]


@router.post("/custom")
def set_custom_quick_adds(
    product_ids: List[int],
    db: Session = Depends(get_db)
):
    """Set custom quick add products (returns product details)"""
    products = db.query(Product)\
        .filter(Product.id.in_(product_ids), Product.is_active == True)\
        .all()
    
    # Maintain order from input
    product_map = {p.id: p for p in products}
    ordered = [product_map[pid] for pid in product_ids if pid in product_map]
    
    return {
        "quick_adds": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category.name if p.category else None
            }
            for p in ordered
        ]
    }
