from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.models import Product, Category
from app.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


def product_to_response(product: Product) -> dict:
    """Convert product model to response with computed fields"""
    data = {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category_id": product.category_id,
        "sku": product.sku,
        "barcode": product.barcode,
        "price": product.price,
        "case_price": product.case_price,
        "case_size": product.case_size,
        "stock_quantity": product.stock_quantity,
        "low_stock_threshold": product.low_stock_threshold,
        "size": product.size,
        "abv": product.abv,
        "description": product.description,
        "requires_age_verification": product.requires_age_verification,
        "is_active": product.is_active,
        "times_sold": product.times_sold,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "category_name": product.category.name if product.category else None,
        "is_low_stock": product.stock_quantity <= product.low_stock_threshold
    }
    return data


@router.get("", response_model=List[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all products with optional filtering"""
    query = db.query(Product)
    
    if active_only:
        query = query.filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    products = query.offset(skip).limit(limit).all()
    return [product_to_response(p) for p in products]


@router.get("/search")
def search_products(
    q: str = Query(..., min_length=1),
    category_id: Optional[int] = None,
    in_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    """Search products by name, brand, or barcode"""
    query = db.query(Product).filter(Product.is_active == True)
    
    # Search across multiple fields
    search_filter = or_(
        Product.name.ilike(f"%{q}%"),
        Product.brand.ilike(f"%{q}%"),
        Product.barcode.ilike(f"%{q}%"),
        Product.sku.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)
    
    products = query.limit(50).all()
    return [product_to_response(p) for p in products]


@router.get("/popular", response_model=List[ProductResponse])
def get_popular_products(limit: int = 10, db: Session = Depends(get_db)):
    """Get most frequently sold products"""
    products = db.query(Product)\
        .filter(Product.is_active == True)\
        .order_by(Product.times_sold.desc())\
        .limit(limit)\
        .all()
    return [product_to_response(p) for p in products]


@router.get("/by-barcode/{barcode}")
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)):
    """Look up product by barcode"""
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_to_response(product)


@router.post("", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    # Validate category exists
    category = db.query(Category).filter(Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    
    # Check for duplicate barcode
    if product.barcode:
        existing = db.query(Product).filter(Product.barcode == product.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")
    
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return product_to_response(db_product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_to_response(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)):
    """Update a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    return product_to_response(product)


@router.patch("/{product_id}/inventory")
def update_inventory(
    product_id: int,
    quantity: int = Query(..., description="New stock quantity"),
    db: Session = Depends(get_db)
):
    """Update product inventory"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock_quantity = quantity
    db.commit()
    
    return {
        "product_id": product_id,
        "name": product.name,
        "stock_quantity": product.stock_quantity,
        "is_low_stock": product.stock_quantity <= product.low_stock_threshold
    }


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Soft delete a product (set inactive)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}
