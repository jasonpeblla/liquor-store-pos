# Gift Cards Router - FR-026
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets

from app.database import get_db
from app.models.gift_card import GiftCard, GiftCardTransaction

router = APIRouter(prefix="/gift-cards", tags=["gift-cards"])


class GiftCardCreate(BaseModel):
    initial_balance: float
    card_type: str = "gift"
    purchased_by: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    expires_in_days: Optional[int] = None


class GiftCardRedeem(BaseModel):
    amount: float
    sale_id: Optional[int] = None


def generate_card_number():
    """Generate 16-digit gift card number"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(16)])


def generate_pin():
    """Generate 4-digit PIN"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(4)])


@router.post("/")
def create_gift_card(card: GiftCardCreate, db: Session = Depends(get_db)):
    """Create and activate a new gift card"""
    card_number = generate_card_number()
    while db.query(GiftCard).filter(GiftCard.card_number == card_number).first():
        card_number = generate_card_number()
    
    expires_at = None
    if card.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=card.expires_in_days)
    
    db_card = GiftCard(
        card_number=card_number,
        pin=generate_pin(),
        initial_balance=card.initial_balance,
        current_balance=card.initial_balance,
        card_type=card.card_type,
        purchased_by=card.purchased_by,
        recipient_name=card.recipient_name,
        recipient_email=card.recipient_email,
        recipient_phone=card.recipient_phone,
        expires_at=expires_at,
        is_active=True,
        activated_at=datetime.utcnow()
    )
    db.add(db_card)
    
    # Record purchase transaction
    db.flush()
    transaction = GiftCardTransaction(
        gift_card_id=db_card.id,
        transaction_type="purchase",
        amount=card.initial_balance,
        balance_after=card.initial_balance
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(db_card)
    return db_card


@router.get("/lookup")
def lookup_gift_card(
    card_number: str,
    pin: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Look up a gift card balance"""
    card = db.query(GiftCard).filter(GiftCard.card_number == card_number).first()
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    
    if pin and card.pin != pin:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    
    if not card.is_active:
        raise HTTPException(status_code=400, detail="Gift card is not active")
    
    if card.expires_at and card.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Gift card has expired")
    
    return {
        "card_number": card.card_number,
        "current_balance": card.current_balance,
        "card_type": card.card_type,
        "is_active": card.is_active,
        "expires_at": card.expires_at.isoformat() if card.expires_at else None
    }


@router.post("/{card_number}/redeem")
def redeem_gift_card(
    card_number: str,
    redemption: GiftCardRedeem,
    db: Session = Depends(get_db)
):
    """Redeem value from a gift card"""
    card = db.query(GiftCard).filter(GiftCard.card_number == card_number).first()
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    
    if not card.is_active:
        raise HTTPException(status_code=400, detail="Gift card is not active")
    
    if card.expires_at and card.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Gift card has expired")
    
    if card.current_balance < redemption.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: ${card.current_balance:.2f}")
    
    card.current_balance -= redemption.amount
    
    transaction = GiftCardTransaction(
        gift_card_id=card.id,
        sale_id=redemption.sale_id,
        transaction_type="redeem",
        amount=-redemption.amount,
        balance_after=card.current_balance
    )
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "amount_redeemed": redemption.amount,
        "remaining_balance": card.current_balance
    }


@router.post("/{card_number}/reload")
def reload_gift_card(card_number: str, amount: float, db: Session = Depends(get_db)):
    """Add value to a gift card"""
    card = db.query(GiftCard).filter(GiftCard.card_number == card_number).first()
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    
    if not card.is_active:
        raise HTTPException(status_code=400, detail="Gift card is not active")
    
    card.current_balance += amount
    
    transaction = GiftCardTransaction(
        gift_card_id=card.id,
        transaction_type="reload",
        amount=amount,
        balance_after=card.current_balance
    )
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "amount_added": amount,
        "new_balance": card.current_balance
    }


@router.get("/{card_number}/transactions")
def get_card_transactions(card_number: str, db: Session = Depends(get_db)):
    """Get transaction history for a gift card"""
    card = db.query(GiftCard).filter(GiftCard.card_number == card_number).first()
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    
    transactions = db.query(GiftCardTransaction).filter(
        GiftCardTransaction.gift_card_id == card.id
    ).order_by(GiftCardTransaction.created_at.desc()).all()
    
    return {"transactions": transactions}


@router.post("/store-credit")
def issue_store_credit(
    customer_id: int,
    amount: float,
    reason: str,
    db: Session = Depends(get_db)
):
    """Issue store credit to a customer"""
    card_number = "SC" + generate_card_number()[2:]
    
    db_card = GiftCard(
        card_number=card_number,
        initial_balance=amount,
        current_balance=amount,
        card_type="store_credit",
        purchased_by=customer_id,
        is_active=True,
        activated_at=datetime.utcnow()
    )
    db.add(db_card)
    db.flush()
    
    transaction = GiftCardTransaction(
        gift_card_id=db_card.id,
        transaction_type="issue",
        amount=amount,
        balance_after=amount,
        notes=reason
    )
    db.add(transaction)
    db.commit()
    db.refresh(db_card)
    
    return db_card


@router.get("/summary")
def get_gift_card_summary(db: Session = Depends(get_db)):
    """Get gift card program summary"""
    total_issued = db.query(func.sum(GiftCard.initial_balance)).filter(
        GiftCard.card_type == "gift"
    ).scalar() or 0
    
    total_outstanding = db.query(func.sum(GiftCard.current_balance)).filter(
        GiftCard.is_active == True
    ).scalar() or 0
    
    active_cards = db.query(func.count(GiftCard.id)).filter(
        GiftCard.is_active == True,
        GiftCard.current_balance > 0
    ).scalar() or 0
    
    return {
        "total_issued": float(total_issued),
        "total_outstanding_liability": float(total_outstanding),
        "active_cards_count": active_cards
    }
