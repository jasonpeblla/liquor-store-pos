from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = 1


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: float
    is_case_price: bool
    discount_applied: float
    line_total: float
    
    class Config:
        from_attributes = True


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItemCreate]
    payment_method: str = "cash"
    age_verified: bool = False


class SaleResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    subtotal: float
    tax_amount: float
    discount_amount: float
    total: float
    payment_method: str
    payment_status: str
    age_verified: bool
    items: List[SaleItemResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True
