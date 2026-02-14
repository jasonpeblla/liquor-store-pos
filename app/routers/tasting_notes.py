from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.tasting_note import TastingNote, ProductReview
from app.models.product import Product

router = APIRouter(prefix="/tasting-notes", tags=["tasting-notes"])


# Schemas
class TastingNoteCreate(BaseModel):
    product_id: int
    nose: Optional[str] = None
    palate: Optional[str] = None
    finish: Optional[str] = None
    vintage: Optional[int] = None
    region: Optional[str] = None
    grape_variety: Optional[str] = None
    staff_rating: Optional[float] = None
    food_pairings: Optional[List[str]] = None
    serve_temp: Optional[str] = None
    decant_time: Optional[str] = None
    glass_type: Optional[str] = None
    description: Optional[str] = None
    staff_pick: bool = False
    created_by: Optional[int] = None


class TastingNoteUpdate(BaseModel):
    nose: Optional[str] = None
    palate: Optional[str] = None
    finish: Optional[str] = None
    vintage: Optional[int] = None
    region: Optional[str] = None
    grape_variety: Optional[str] = None
    staff_rating: Optional[float] = None
    food_pairings: Optional[List[str]] = None
    serve_temp: Optional[str] = None
    decant_time: Optional[str] = None
    glass_type: Optional[str] = None
    description: Optional[str] = None
    staff_pick: Optional[bool] = None
    is_active: Optional[bool] = None


class TastingNoteResponse(BaseModel):
    id: int
    product_id: int
    nose: Optional[str]
    palate: Optional[str]
    finish: Optional[str]
    vintage: Optional[int]
    region: Optional[str]
    grape_variety: Optional[str]
    staff_rating: Optional[float]
    food_pairings: Optional[List[str]]
    serve_temp: Optional[str]
    decant_time: Optional[str]
    glass_type: Optional[str]
    description: Optional[str]
    staff_pick: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    product_id: int
    customer_id: Optional[int] = None
    rating: int  # 1-5
    title: Optional[str] = None
    review_text: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    customer_id: Optional[int]
    rating: int
    title: Optional[str]
    review_text: Optional[str]
    verified_purchase: bool
    is_featured: bool
    helpful_votes: int
    created_at: datetime

    class Config:
        from_attributes = True


# Tasting Note Routes
@router.get("", response_model=List[TastingNoteResponse])
def list_tasting_notes(
    staff_picks_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all tasting notes"""
    query = db.query(TastingNote).filter(TastingNote.is_active == True)
    
    if staff_picks_only:
        query = query.filter(TastingNote.staff_pick == True)
    
    return query.order_by(TastingNote.created_at.desc()).all()


@router.get("/product/{product_id}", response_model=TastingNoteResponse)
def get_product_tasting_note(product_id: int, db: Session = Depends(get_db)):
    """Get tasting note for a specific product"""
    note = db.query(TastingNote).filter(
        TastingNote.product_id == product_id,
        TastingNote.is_active == True
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Tasting note not found for this product")
    
    return note


@router.get("/staff-picks")
def get_staff_picks(
    limit: int = 10,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get staff pick products with tasting notes"""
    query = db.query(TastingNote, Product).join(
        Product, TastingNote.product_id == Product.id
    ).filter(
        TastingNote.is_active == True,
        TastingNote.staff_pick == True,
        Product.is_active == True
    )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    results = query.order_by(TastingNote.staff_rating.desc()).limit(limit).all()
    
    return [
        {
            "product_id": product.id,
            "product_name": product.name,
            "brand": product.brand,
            "price": product.price,
            "staff_rating": note.staff_rating,
            "description": note.description,
            "food_pairings": note.food_pairings,
            "vintage": note.vintage,
            "region": note.region
        }
        for note, product in results
    ]


@router.post("", response_model=TastingNoteResponse)
def create_tasting_note(data: TastingNoteCreate, db: Session = Depends(get_db)):
    """Create a tasting note for a product"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if note already exists
    existing = db.query(TastingNote).filter(
        TastingNote.product_id == data.product_id,
        TastingNote.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Tasting note already exists for this product")
    
    note = TastingNote(**data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/{note_id}", response_model=TastingNoteResponse)
def update_tasting_note(note_id: int, data: TastingNoteUpdate, db: Session = Depends(get_db)):
    """Update a tasting note"""
    note = db.query(TastingNote).filter(TastingNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Tasting note not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(note, key, value)
    
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}")
def delete_tasting_note(note_id: int, db: Session = Depends(get_db)):
    """Soft delete a tasting note"""
    note = db.query(TastingNote).filter(TastingNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Tasting note not found")
    
    note.is_active = False
    db.commit()
    return {"message": "Tasting note deleted"}


# Review Routes
@router.get("/reviews/product/{product_id}")
def get_product_reviews(
    product_id: int,
    approved_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get reviews for a product"""
    query = db.query(ProductReview).filter(ProductReview.product_id == product_id)
    
    if approved_only:
        query = query.filter(ProductReview.is_approved == True)
    
    reviews = query.order_by(ProductReview.created_at.desc()).all()
    
    # Calculate average
    avg_rating = db.query(func.avg(ProductReview.rating)).filter(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True
    ).scalar()
    
    return {
        "product_id": product_id,
        "average_rating": round(avg_rating, 1) if avg_rating else None,
        "review_count": len(reviews),
        "reviews": reviews
    }


@router.post("/reviews", response_model=ReviewResponse)
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    """Create a product review"""
    # Validate rating
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if customer has purchased this product (for verified_purchase)
    verified = False
    if data.customer_id:
        from app.models.sale import Sale
        from app.models.sale_item import SaleItem
        
        purchase = db.query(SaleItem).join(Sale).filter(
            Sale.customer_id == data.customer_id,
            SaleItem.product_id == data.product_id
        ).first()
        verified = purchase is not None
    
    review = ProductReview(
        product_id=data.product_id,
        customer_id=data.customer_id,
        rating=data.rating,
        title=data.title,
        review_text=data.review_text,
        verified_purchase=verified
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.post("/reviews/{review_id}/helpful")
def mark_helpful(review_id: int, db: Session = Depends(get_db)):
    """Mark a review as helpful"""
    review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.helpful_votes += 1
    db.commit()
    return {"message": "Marked as helpful", "helpful_votes": review.helpful_votes}


@router.post("/reviews/{review_id}/feature")
def toggle_featured(review_id: int, db: Session = Depends(get_db)):
    """Toggle featured status for a review"""
    review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review.is_featured = not review.is_featured
    db.commit()
    return {"message": f"Review {'featured' if review.is_featured else 'unfeatured'}", "is_featured": review.is_featured}


@router.get("/wines/by-region")
def wines_by_region(db: Session = Depends(get_db)):
    """Group wines by region from tasting notes"""
    notes = db.query(TastingNote, Product).join(
        Product, TastingNote.product_id == Product.id
    ).filter(
        TastingNote.is_active == True,
        TastingNote.region != None,
        Product.is_active == True
    ).all()
    
    regions = {}
    for note, product in notes:
        if note.region not in regions:
            regions[note.region] = []
        regions[note.region].append({
            "product_id": product.id,
            "name": product.name,
            "brand": product.brand,
            "price": product.price,
            "vintage": note.vintage,
            "grape_variety": note.grape_variety,
            "staff_rating": note.staff_rating
        })
    
    return regions


@router.get("/food-pairing/{food}")
def find_by_food_pairing(food: str, db: Session = Depends(get_db)):
    """Find products that pair with a specific food"""
    # This is a simple implementation; JSON contains search varies by DB
    notes = db.query(TastingNote, Product).join(
        Product, TastingNote.product_id == Product.id
    ).filter(
        TastingNote.is_active == True,
        TastingNote.food_pairings != None,
        Product.is_active == True
    ).all()
    
    matches = []
    for note, product in notes:
        if note.food_pairings:
            for pairing in note.food_pairings:
                if food.lower() in pairing.lower():
                    matches.append({
                        "product_id": product.id,
                        "name": product.name,
                        "brand": product.brand,
                        "price": product.price,
                        "food_pairings": note.food_pairings,
                        "description": note.description
                    })
                    break
    
    return matches
