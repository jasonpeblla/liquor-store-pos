# Gift Card & Store Credit Model - FR-026
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from datetime import datetime
from app.database import Base


class GiftCard(Base):
    """Gift cards and store credit"""
    __tablename__ = "gift_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    card_number = Column(String, unique=True, nullable=False, index=True)
    pin = Column(String, nullable=True)
    
    # Balance
    initial_balance = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    
    # Type
    card_type = Column(String, default="gift")  # gift, store_credit, promotional
    
    # Purchaser
    purchased_by = Column(Integer, ForeignKey("customers.id"), nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    
    # Recipient
    recipient_name = Column(String, nullable=True)
    recipient_email = Column(String, nullable=True)
    recipient_phone = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class GiftCardTransaction(Base):
    """Track gift card usage"""
    __tablename__ = "gift_card_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    gift_card_id = Column(Integer, ForeignKey("gift_cards.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    
    # Transaction
    transaction_type = Column(String, nullable=False)  # purchase, redeem, refund, void
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Reference
    employee_id = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
