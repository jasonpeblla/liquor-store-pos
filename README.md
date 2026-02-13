# Liquor Store POS

A modern point-of-sale system designed for liquor stores, featuring product catalog management, age verification, inventory tracking, and bulk pricing.

## Features

- **Product Catalog**: Beer, wine, spirits, mixers with detailed info
- **Age Verification**: Built-in prompts for alcohol sales compliance
- **Inventory Management**: Real-time stock tracking with low-stock alerts
- **Bulk Pricing**: Case discounts and volume-based pricing
- **Smart Search**: Find products by name, brand, type, or category
- **Tax Calculation**: Configurable alcohol tax rates
- **Popular Items**: Track and display best sellers

## Quick Start

### Backend (FastAPI)

```bash
cd ~/liquor-store-pos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev -- --port 3005
```

## API Endpoints

- `GET /products` - List all products
- `GET /products/search?q=` - Search products
- `GET /products/{id}` - Get product details
- `POST /products` - Create product
- `PATCH /products/{id}/inventory` - Update stock
- `GET /categories` - List categories
- `POST /sales` - Create a sale (with age verification)
- `GET /sales` - List sales
- `GET /inventory/low-stock` - Get low stock alerts

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + Vite + Tailwind CSS
- **Ports**: Backend 8003, Frontend 3005
