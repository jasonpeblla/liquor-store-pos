from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base, SessionLocal
from app.routers import (
    products_router, categories_router, sales_router,
    customers_router, inventory_router, receipts_router,
    reports_router, barcode_router, promotions_router,
    loyalty_router, age_verification_router
)
from app.models import Category, Product


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default categories and products
    db = SessionLocal()
    try:
        if db.query(Category).count() == 0:
            # Create categories with alcohol tax rates
            categories = [
                Category(name="Beer", description="Domestic and imported beers", tax_rate=0.02),
                Category(name="Wine", description="Red, white, rosé, and sparkling wines", tax_rate=0.03),
                Category(name="Spirits", description="Whiskey, vodka, rum, tequila, gin", tax_rate=0.05),
                Category(name="Mixers", description="Sodas, juices, tonic water", tax_rate=0.0),
                Category(name="Snacks", description="Chips, nuts, bar snacks", tax_rate=0.0),
                Category(name="Accessories", description="Corkscrews, glasses, ice", tax_rate=0.0),
            ]
            for cat in categories:
                db.add(cat)
            db.commit()
            
            # Seed some sample products
            beer_cat = db.query(Category).filter(Category.name == "Beer").first()
            wine_cat = db.query(Category).filter(Category.name == "Wine").first()
            spirits_cat = db.query(Category).filter(Category.name == "Spirits").first()
            mixers_cat = db.query(Category).filter(Category.name == "Mixers").first()
            
            products = [
                # Beer
                Product(name="Budweiser", brand="Anheuser-Busch", category_id=beer_cat.id, 
                       price=1.99, case_price=19.99, case_size=12, stock_quantity=48, 
                       size="12oz can", abv=5.0, barcode="018200002717"),
                Product(name="Corona Extra", brand="Grupo Modelo", category_id=beer_cat.id,
                       price=2.49, case_price=27.99, case_size=12, stock_quantity=36,
                       size="12oz bottle", abv=4.6, barcode="018200002724"),
                Product(name="Heineken", brand="Heineken", category_id=beer_cat.id,
                       price=2.29, case_price=25.99, case_size=12, stock_quantity=24,
                       size="12oz bottle", abv=5.0, barcode="018200002731"),
                Product(name="IPA 6-Pack", brand="Lagunitas", category_id=beer_cat.id,
                       price=12.99, stock_quantity=18, size="6-pack", abv=6.2),
                
                # Wine
                Product(name="Cabernet Sauvignon", brand="Robert Mondavi", category_id=wine_cat.id,
                       price=14.99, case_price=149.99, case_size=12, stock_quantity=15,
                       size="750ml", abv=13.5, barcode="018200003001"),
                Product(name="Chardonnay", brand="Kendall-Jackson", category_id=wine_cat.id,
                       price=12.99, case_price=129.99, case_size=12, stock_quantity=20,
                       size="750ml", abv=13.5, barcode="018200003002"),
                Product(name="Pinot Grigio", brand="Santa Margherita", category_id=wine_cat.id,
                       price=19.99, stock_quantity=12, size="750ml", abv=12.0),
                Product(name="Prosecco", brand="La Marca", category_id=wine_cat.id,
                       price=15.99, stock_quantity=8, size="750ml", abv=11.0),
                
                # Spirits
                Product(name="Tito's Vodka", brand="Tito's", category_id=spirits_cat.id,
                       price=24.99, stock_quantity=25, size="750ml", abv=40.0, barcode="619947000020"),
                Product(name="Jack Daniel's", brand="Jack Daniel's", category_id=spirits_cat.id,
                       price=27.99, stock_quantity=18, size="750ml", abv=40.0, barcode="082184090466"),
                Product(name="Patron Silver", brand="Patron", category_id=spirits_cat.id,
                       price=44.99, stock_quantity=10, size="750ml", abv=40.0),
                Product(name="Bacardi White Rum", brand="Bacardi", category_id=spirits_cat.id,
                       price=16.99, stock_quantity=22, size="750ml", abv=40.0),
                Product(name="Hendrick's Gin", brand="Hendrick's", category_id=spirits_cat.id,
                       price=34.99, stock_quantity=8, size="750ml", abv=41.4),
                
                # Mixers (no age verification needed)
                Product(name="Tonic Water", brand="Schweppes", category_id=mixers_cat.id,
                       price=1.49, stock_quantity=30, size="1L", requires_age_verification=False),
                Product(name="Club Soda", brand="Canada Dry", category_id=mixers_cat.id,
                       price=1.29, stock_quantity=25, size="1L", requires_age_verification=False),
                Product(name="Lime Juice", brand="Rose's", category_id=mixers_cat.id,
                       price=4.99, stock_quantity=15, size="12oz", requires_age_verification=False),
            ]
            
            for product in products:
                db.add(product)
            db.commit()
    finally:
        db.close()
    
    yield
    # Shutdown


app = FastAPI(
    title="Liquor Store POS",
    description="Point of sale system for liquor stores with age verification and inventory management",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(sales_router)
app.include_router(customers_router)
app.include_router(inventory_router)
app.include_router(receipts_router)
app.include_router(reports_router)
app.include_router(barcode_router)
app.include_router(promotions_router)
app.include_router(loyalty_router)
app.include_router(age_verification_router)


@app.get("/")
def root():
    return {
        "name": "Liquor Store POS",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
