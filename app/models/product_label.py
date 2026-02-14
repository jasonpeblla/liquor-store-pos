# Product Labels - FR-034
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from datetime import datetime
from app.database import Base


class LabelTemplate(Base):
    """Label templates for printing"""
    __tablename__ = "label_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String, nullable=False)
    template_type = Column(String, default="price")  # price, shelf, barcode, case
    
    # Dimensions (in inches)
    width = Column(Float, default=2.0)
    height = Column(Float, default=1.0)
    
    # Layout configuration (JSON)
    layout = Column(Text, nullable=True)  # Contains field positions, fonts, etc.
    
    # Fields to include
    show_price = Column(Boolean, default=True)
    show_barcode = Column(Boolean, default=True)
    show_product_name = Column(Boolean, default=True)
    show_brand = Column(Boolean, default=False)
    show_size = Column(Boolean, default=True)
    show_abv = Column(Boolean, default=False)
    show_case_price = Column(Boolean, default=False)
    show_unit_price = Column(Boolean, default=False)
    
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class LabelPrintJob(Base):
    """Label print job queue"""
    __tablename__ = "label_print_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    template_id = Column(Integer, ForeignKey("label_templates.id"), nullable=False)
    product_ids = Column(Text, nullable=False)  # Comma-separated
    
    quantity_per_product = Column(Integer, default=1)
    total_labels = Column(Integer, default=0)
    
    status = Column(String, default="pending")  # pending, printing, completed, failed
    
    requested_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    printed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ShelfTag(Base):
    """Shelf tags with extended info"""
    __tablename__ = "shelf_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Location
    aisle = Column(String, nullable=True)
    section = Column(String, nullable=True)
    shelf_position = Column(String, nullable=True)
    
    # Display info
    display_name = Column(String, nullable=True)  # Override product name
    callout_text = Column(String, nullable=True)  # e.g., "Staff Pick!", "New Arrival"
    
    # Dates
    last_printed = Column(DateTime, nullable=True)
    price_changed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
