from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # "bug" or "feature"
    message = Column(Text, nullable=False)
    email = Column(String(255), nullable=True)
    page_url = Column(String(500), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(50), default="new")  # new, reviewed, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
