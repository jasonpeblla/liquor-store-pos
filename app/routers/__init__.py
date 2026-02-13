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

__all__ = [
    "products_router", "categories_router", "sales_router", 
    "customers_router", "inventory_router", "receipts_router",
    "reports_router", "barcode_router", "promotions_router",
    "loyalty_router", "age_verification_router"
]
