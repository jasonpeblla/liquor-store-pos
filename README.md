# Liquor Store POS

A comprehensive point-of-sale system designed for liquor stores, featuring age verification, inventory management, promotions, loyalty programs, and compliance tracking.

## Features

### Core POS
- **Product Catalog**: Beer, wine, spirits, mixers with detailed info
- **Shopping Cart**: Add/remove items, quantity management
- **Checkout**: Cash and card payment support
- **Receipt Generation**: Formatted receipts with all sale details

### Compliance
- **Age Verification**: 21+ prompts for alcohol sales
- **Verification History**: Audit trail for compliance
- **Declined Tracking**: Records of refused sales

### Pricing & Discounts
- **Case/Bulk Pricing**: Automatic discounts for case purchases
- **Promotions**: Percentage, fixed amount, BOGO deals
- **Category Taxes**: Variable alcohol tax rates

### Inventory
- **Stock Tracking**: Real-time inventory levels
- **Low Stock Alerts**: Configurable thresholds
- **Barcode Support**: Scan products for quick lookup

### Customer Management
- **Loyalty Program**: Tiered rewards (Bronze → Platinum)
- **Points System**: Earn and redeem loyalty points
- **Purchase History**: Track customer spending

### Operations
- **Shift Management**: Start/end shifts with cash reconciliation
- **Reports**: Daily, weekly, hourly sales analytics
- **Quick Add**: Favorites for rapid checkout

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

### Products
- `GET /products` - List all products
- `GET /products/search?q=` - Search products
- `GET /products/popular` - Top sellers
- `GET /products/by-barcode/{barcode}` - Barcode lookup
- `POST /products` - Create product
- `PATCH /products/{id}/inventory` - Update stock

### Sales
- `GET /sales` - List sales
- `POST /sales` - Create sale (requires age_verified for alcohol)
- `GET /sales/{id}` - Get sale details
- `POST /sales/{id}/refund` - Refund a sale

### Inventory
- `GET /inventory/low-stock` - Low stock alerts
- `GET /inventory/out-of-stock` - Out of stock items
- `GET /inventory/summary` - Inventory by category
- `POST /inventory/bulk-update` - Bulk stock update

### Receipts
- `GET /receipts/{sale_id}` - Get receipt
- `GET /receipts/{sale_id}/print` - Print receipt

### Reports
- `GET /reports/daily` - Daily report
- `GET /reports/weekly` - Weekly overview
- `GET /reports/top-products` - Best sellers
- `GET /reports/category-breakdown` - Sales by category
- `GET /reports/hourly` - Hourly traffic

### Barcode
- `GET /barcode/scan/{code}` - Scan lookup
- `POST /barcode/bulk-lookup` - Batch lookup
- `POST /barcode/assign` - Assign barcode

### Promotions
- `GET /promotions` - List active promotions
- `POST /promotions` - Create promotion
- `POST /promotions/calculate` - Calculate cart discounts

### Loyalty
- `GET /loyalty/customer/{id}` - Customer loyalty status
- `POST /loyalty/customer/{id}/redeem` - Redeem points
- `GET /loyalty/leaderboard` - Top customers
- `POST /loyalty/lookup-by-phone` - Phone lookup

### Age Verification
- `POST /age-verification/verify` - Record verification
- `GET /age-verification/check/{customer_id}` - Check status
- `GET /age-verification/history` - Verification history
- `GET /age-verification/declined` - Declined records

### Shifts
- `GET /shifts/current` - Current shift status
- `POST /shifts/start` - Start shift
- `POST /shifts/end` - End shift with reconciliation
- `GET /shifts/history` - Shift history

### Settings
- `GET /settings` - All settings
- `GET /settings/pos-config` - Frontend config
- `POST /settings/update` - Update settings

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + Vite + Tailwind CSS
- **Ports**: Backend 8003, Frontend 3005

## Sample Data

The system seeds with:
- 6 categories (Beer, Wine, Spirits, Mixers, Snacks, Accessories)
- 16 sample products with realistic pricing
- Category-specific tax rates

## License

MIT
