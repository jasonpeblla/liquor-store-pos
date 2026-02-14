from .products import router as products_router
from .categories import router as categories_router
from .sales import router as sales_router
from .customers import router as customers_router
from .inventory import router as inventory_router
from .receipts import router as receipts_router
from .reports import router as reports_router
from .barcode import router as barcode_router
from .promotions import router as promotions_router
from .loyalty import router as loyalty_router
from .age_verification import router as age_verification_router
from .shifts import router as shifts_router
from .quick_add import router as quick_add_router
from .settings import router as settings_router
from .feedback import router as feedback_router
from .suppliers import router as suppliers_router
from .purchase_orders import router as purchase_orders_router
from .happy_hour import router as happy_hour_router
from .mix_match import router as mix_match_router
from .bottle_deposits import router as bottle_deposits_router
from .employees import router as employees_router
from .compliance import router as compliance_router
from .reservations import router as reservations_router
from .tasting_notes import router as tasting_notes_router
from .quantity_limits import router as quantity_limits_router
from .dashboard import router as dashboard_router
from .wine_vintages import router as wine_vintages_router
from .craft_beer import router as craft_beer_router
from .gift_cards import router as gift_cards_router
from .tasting_events import router as tasting_events_router
from .delivery import router as delivery_router

__all__ = [
    "products_router", "categories_router", "sales_router", 
    "customers_router", "inventory_router", "receipts_router",
    "reports_router", "barcode_router", "promotions_router",
    "loyalty_router", "age_verification_router", "shifts_router",
    "quick_add_router", "settings_router", "feedback_router",
    "suppliers_router",
    "purchase_orders_router",
    "happy_hour_router",
    "mix_match_router",
    "bottle_deposits_router",
    "employees_router",
    "compliance_router",
    "reservations_router",
    "tasting_notes_router",
    "quantity_limits_router",
    "dashboard_router",
    "wine_vintages_router",
    "craft_beer_router",
    "gift_cards_router",
    "tasting_events_router",
    "delivery_router"
]
