from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.models.feedback import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    type: str  # "bug" or "feature"
    message: str
    email: Optional[str] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    type: str
    message: str
    email: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=FeedbackResponse)
def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    db_feedback = Feedback(**feedback.model_dump())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback


@router.get("/", response_model=List[FeedbackResponse])
def list_feedback(
    type: str = None,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Feedback)
    if type:
        query = query.filter(Feedback.type == type)
    if status:
        query = query.filter(Feedback.status == status)
    return query.order_by(Feedback.created_at.desc()).limit(limit).all()
