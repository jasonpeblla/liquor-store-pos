from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/barcode", tags=["barcode"])


@router.get("/scan/{code}")
def scan_barcode(code: str, db: Session = Depends(get_db)):
    """Scan a barcode and return product info for quick add to cart"""
    # Try to find by barcode first
    product = db.query(Product).filter(Product.barcode == code).first()
    
    # If not found, try SKU
    if not product:
        product = db.query(Product).filter(Product.sku == code).first()
    
    if not product:
        return {
            "found": False,
            "barcode": code,
            "message": "Product not found"
        }
    
    if not product.is_active:
        return {
            "found": False,
            "barcode": code,
            "message": "Product is discontinued"
        }
    
    return {
        "found": True,
        "barcode": code,
        "product": {
            "id": product.id,
            "name": product.name,
            "brand": product.brand,
            "price": product.price,
            "case_price": product.case_price,
            "case_size": product.case_size,
            "size": product.size,
            "stock_quantity": product.stock_quantity,
            "requires_age_verification": product.requires_age_verification,
            "in_stock": product.stock_quantity > 0,
            "is_low_stock": product.stock_quantity <= product.low_stock_threshold
        }
    }


@router.post("/bulk-lookup")
def bulk_barcode_lookup(codes: list, db: Session = Depends(get_db)):
    """Look up multiple barcodes at once"""
    results = []
    
    for code in codes:
        product = db.query(Product).filter(
            (Product.barcode == code) | (Product.sku == code)
        ).first()
        
        if product and product.is_active:
            results.append({
                "code": code,
                "found": True,
                "product_id": product.id,
                "name": product.name,
                "price": product.price
            })
        else:
            results.append({
                "code": code,
                "found": False
            })
    
    return {
        "total": len(codes),
        "found": sum(1 for r in results if r["found"]),
        "results": results
    }


@router.post("/assign")
def assign_barcode(
    product_id: int,
    barcode: str,
    db: Session = Depends(get_db)
):
    """Assign a barcode to a product"""
    # Check if barcode already exists
    existing = db.query(Product).filter(Product.barcode == barcode).first()
    if existing and existing.id != product_id:
        raise HTTPException(
            status_code=400,
            detail=f"Barcode already assigned to {existing.name}"
        )
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.barcode = barcode
    db.commit()
    
    return {
        "success": True,
        "product_id": product_id,
        "barcode": barcode,
        "product_name": product.name
    }
