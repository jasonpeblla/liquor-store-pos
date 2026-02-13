from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    category_id: int
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price: float
    case_price: Optional[float] = None
    case_size: int = 12
    stock_quantity: int = 0
    low_stock_threshold: int = 10
    size: Optional[str] = None
    abv: Optional[float] = None
    description: Optional[str] = None
    requires_age_verification: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    case_price: Optional[float] = None
    case_size: Optional[int] = None
    stock_quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    size: Optional[str] = None
    abv: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    times_sold: int
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = None
    is_low_stock: bool = False
    
    class Config:
        from_attributes = True


class ProductSearch(BaseModel):
    query: Optional[str] = None
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock_only: bool = False
