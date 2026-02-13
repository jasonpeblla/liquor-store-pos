from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[date] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    id_verified: bool
    id_verified_at: Optional[datetime] = None
    loyalty_points: int
    total_spent: float
    created_at: datetime
    
    class Config:
        from_attributes = True
