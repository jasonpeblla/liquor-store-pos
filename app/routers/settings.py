from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

# Default settings (in production, would be stored in DB)
STORE_SETTINGS = {
    "store_name": "Liquor Store POS",
    "store_address": "123 Main Street",
    "store_phone": "(555) 123-4567",
    "tax_rates": {
        "base_sales_tax": 0.0875,
        "beer_tax": 0.02,
        "wine_tax": 0.03,
        "spirits_tax": 0.05
    },
    "age_verification": {
        "minimum_age": 21,
        "require_for_all_alcohol": True,
        "save_verification_history": True
    },
    "loyalty": {
        "points_per_dollar": 1,
        "points_redemption_ratio": 100,
        "enabled": True
    },
    "inventory": {
        "default_low_stock_threshold": 10,
        "show_out_of_stock": False,
        "allow_negative_stock": False
    },
    "receipt": {
        "print_automatically": True,
        "show_savings": True,
        "footer_message": "Thank you! Please drink responsibly."
    },
    "shifts": {
        "require_shift_start": True,
        "default_opening_cash": 200.0
    }
}


@router.get("")
def get_all_settings():
    """Get all store settings"""
    return STORE_SETTINGS


@router.get("/store")
def get_store_info():
    """Get store information"""
    return {
        "name": STORE_SETTINGS["store_name"],
        "address": STORE_SETTINGS["store_address"],
        "phone": STORE_SETTINGS["store_phone"]
    }


@router.get("/tax-rates")
def get_tax_rates():
    """Get all tax rates"""
    return STORE_SETTINGS["tax_rates"]


@router.get("/age-verification")
def get_age_verification_settings():
    """Get age verification settings"""
    return STORE_SETTINGS["age_verification"]


@router.get("/loyalty")
def get_loyalty_settings():
    """Get loyalty program settings"""
    return STORE_SETTINGS["loyalty"]


@router.get("/inventory")
def get_inventory_settings():
    """Get inventory settings"""
    return STORE_SETTINGS["inventory"]


@router.get("/receipt")
def get_receipt_settings():
    """Get receipt settings"""
    return STORE_SETTINGS["receipt"]


@router.post("/update")
def update_settings(updates: Dict[str, Any]):
    """Update settings (in-memory only for demo)"""
    for key, value in updates.items():
        if key in STORE_SETTINGS:
            if isinstance(STORE_SETTINGS[key], dict) and isinstance(value, dict):
                STORE_SETTINGS[key].update(value)
            else:
                STORE_SETTINGS[key] = value
    
    return {"message": "Settings updated", "current_settings": STORE_SETTINGS}


@router.get("/pos-config")
def get_pos_config():
    """Get essential POS configuration for frontend"""
    return {
        "store_name": STORE_SETTINGS["store_name"],
        "minimum_age": STORE_SETTINGS["age_verification"]["minimum_age"],
        "require_age_verification": STORE_SETTINGS["age_verification"]["require_for_all_alcohol"],
        "loyalty_enabled": STORE_SETTINGS["loyalty"]["enabled"],
        "points_per_dollar": STORE_SETTINGS["loyalty"]["points_per_dollar"],
        "base_tax_rate": STORE_SETTINGS["tax_rates"]["base_sales_tax"],
        "receipt_footer": STORE_SETTINGS["receipt"]["footer_message"],
        "require_shift": STORE_SETTINGS["shifts"]["require_shift_start"]
    }
