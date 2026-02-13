from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Sale, Product

router = APIRouter(prefix="/receipts", tags=["receipts"])


def generate_receipt_text(sale: Sale, db: Session) -> str:
    """Generate a text receipt for a sale"""
    lines = []
    lines.append("=" * 40)
    lines.append("        LIQUOR STORE POS")
    lines.append("=" * 40)
    lines.append(f"Receipt #: {sale.id}")
    lines.append(f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    if sale.customer:
        lines.append(f"Customer: {sale.customer.name}")
    lines.append("-" * 40)
    
    for item in sale.items:
        product_name = item.product.name if item.product else f"Product #{item.product_id}"
        qty_price = f"{item.quantity} x ${item.unit_price:.2f}"
        line_total = f"${item.line_total:.2f}"
        
        lines.append(f"{product_name}")
        lines.append(f"  {qty_price:30} {line_total:>8}")
        
        if item.is_case_price:
            lines.append("  (Case discount applied)")
    
    lines.append("-" * 40)
    lines.append(f"{'Subtotal':32} ${sale.subtotal:>7.2f}")
    lines.append(f"{'Tax':32} ${sale.tax_amount:>7.2f}")
    if sale.discount_amount > 0:
        lines.append(f"{'Discount':32} -${sale.discount_amount:>6.2f}")
    lines.append("=" * 40)
    lines.append(f"{'TOTAL':32} ${sale.total:>7.2f}")
    lines.append("=" * 40)
    lines.append(f"Payment: {sale.payment_method.upper()}")
    
    if sale.age_verified:
        lines.append("")
        lines.append("** Age verified for alcohol purchase **")
    
    lines.append("")
    lines.append("       Thank you for your purchase!")
    lines.append("          Please drink responsibly")
    lines.append("")
    
    return "\n".join(lines)


@router.get("/{sale_id}")
def get_receipt(sale_id: int, db: Session = Depends(get_db)):
    """Get a receipt for a sale"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    return {
        "sale_id": sale_id,
        "receipt_text": generate_receipt_text(sale, db),
        "created_at": sale.created_at,
        "total": sale.total
    }


@router.get("/{sale_id}/print")
def print_receipt(sale_id: int, db: Session = Depends(get_db)):
    """Mock print receipt (returns receipt data for printing)"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    receipt_text = generate_receipt_text(sale, db)
    
    return {
        "status": "printed",
        "sale_id": sale_id,
        "receipt_text": receipt_text,
        "printed_at": datetime.utcnow().isoformat()
    }
