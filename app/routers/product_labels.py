# Product Labels Router - FR-034
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.product_label import LabelTemplate, LabelPrintJob, ShelfTag
from app.models import Product

router = APIRouter(prefix="/labels", tags=["labels"])


class TemplateCreate(BaseModel):
    name: str
    template_type: str = "price"
    width: float = 2.0
    height: float = 1.0
    show_price: bool = True
    show_barcode: bool = True
    show_product_name: bool = True
    show_brand: bool = False
    show_size: bool = True
    show_abv: bool = False
    show_case_price: bool = False


class PrintJobCreate(BaseModel):
    template_id: int
    product_ids: List[int]
    quantity_per_product: int = 1


class ShelfTagCreate(BaseModel):
    product_id: int
    aisle: Optional[str] = None
    section: Optional[str] = None
    shelf_position: Optional[str] = None
    display_name: Optional[str] = None
    callout_text: Optional[str] = None


# Template endpoints
@router.post("/templates")
def create_template(template: TemplateCreate, db: Session = Depends(get_db)):
    """Create a label template"""
    db_template = LabelTemplate(**template.dict(), is_active=True)
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/templates")
def list_templates(template_type: Optional[str] = None, db: Session = Depends(get_db)):
    """List label templates"""
    query = db.query(LabelTemplate).filter(LabelTemplate.is_active == True)
    if template_type:
        query = query.filter(LabelTemplate.template_type == template_type)
    return query.all()


@router.get("/templates/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get template details"""
    template = db.query(LabelTemplate).filter(LabelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


# Print job endpoints
@router.post("/print")
def create_print_job(job: PrintJobCreate, db: Session = Depends(get_db)):
    """Create a label print job"""
    template = db.query(LabelTemplate).filter(LabelTemplate.id == job.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db_job = LabelPrintJob(
        template_id=job.template_id,
        product_ids=",".join(str(p) for p in job.product_ids),
        quantity_per_product=job.quantity_per_product,
        total_labels=len(job.product_ids) * job.quantity_per_product
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job


@router.get("/print/queue")
def get_print_queue(db: Session = Depends(get_db)):
    """Get pending print jobs"""
    jobs = db.query(LabelPrintJob).filter(
        LabelPrintJob.status == "pending"
    ).order_by(LabelPrintJob.created_at).all()
    return jobs


@router.post("/print/{job_id}/complete")
def complete_print_job(job_id: int, db: Session = Depends(get_db)):
    """Mark print job as completed"""
    job = db.query(LabelPrintJob).filter(LabelPrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "completed"
    job.printed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Print job completed"}


@router.post("/print/batch")
def print_batch(
    category_id: Optional[int] = None,
    price_changed_since: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Generate batch print job for products"""
    query = db.query(Product)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    products = query.all()
    product_ids = [p.id for p in products]
    
    # Get default template
    template = db.query(LabelTemplate).filter(
        LabelTemplate.is_default == True,
        LabelTemplate.is_active == True
    ).first()
    
    if not template:
        template = db.query(LabelTemplate).filter(LabelTemplate.is_active == True).first()
    
    if not template:
        raise HTTPException(status_code=400, detail="No active templates available")
    
    job = LabelPrintJob(
        template_id=template.id,
        product_ids=",".join(str(p) for p in product_ids),
        quantity_per_product=1,
        total_labels=len(product_ids)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {"job": job, "products_count": len(product_ids)}


# Shelf tag endpoints
@router.post("/shelf-tags")
def create_shelf_tag(tag: ShelfTagCreate, db: Session = Depends(get_db)):
    """Create or update shelf tag"""
    existing = db.query(ShelfTag).filter(ShelfTag.product_id == tag.product_id).first()
    
    if existing:
        for key, value in tag.dict().items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    db_tag = ShelfTag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.get("/shelf-tags")
def list_shelf_tags(
    aisle: Optional[str] = None,
    section: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List shelf tags"""
    query = db.query(ShelfTag)
    if aisle:
        query = query.filter(ShelfTag.aisle == aisle)
    if section:
        query = query.filter(ShelfTag.section == section)
    return query.all()


@router.get("/shelf-tags/by-location")
def get_tags_by_location(db: Session = Depends(get_db)):
    """Get shelf tags organized by location"""
    tags = db.query(ShelfTag).all()
    
    by_aisle = {}
    for tag in tags:
        aisle = tag.aisle or "Unassigned"
        if aisle not in by_aisle:
            by_aisle[aisle] = []
        by_aisle[aisle].append(tag)
    
    return by_aisle
