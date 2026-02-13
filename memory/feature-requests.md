# Feature Requests

## Backlog

### FR-001: Core POS System
- **Priority:** P0
- **Effort:** L
- **Status:** Done
- **Problem:** Need basic POS functionality for liquor store
- **Solution:** Create full-stack POS with product catalog, cart, and checkout
- **Acceptance Criteria:**
  - [x] Product listing by category
  - [x] Product search
  - [x] Shopping cart functionality
  - [x] Checkout with payment method selection
  - [x] Age verification for alcohol products
  - [x] Inventory tracking
  - [x] Low stock alerts

### FR-002: Case/Bulk Pricing
- **Priority:** P1
- **Effort:** M
- **Status:** Done
- **Problem:** Liquor stores offer case discounts
- **Solution:** Implement case pricing that auto-applies when quantity >= case_size
- **Acceptance Criteria:**
  - [x] Products can have case_price and case_size
  - [x] Cart automatically calculates case discounts
  - [x] UI shows case pricing info

### FR-003: Age Verification Flow
- **Priority:** P0
- **Effort:** S
- **Status:** Done
- **Problem:** Legal requirement to verify 21+ for alcohol sales
- **Solution:** Modal prompt for age verification before adding alcohol to cart
- **Acceptance Criteria:**
  - [x] Products flagged as requiring age verification
  - [x] Modal appears on first alcohol add
  - [x] Status persists for session
  - [x] Sales record age verification

---

## Completed

| FR# | Title | Date |
|-----|-------|------|
| FR-001 | Core POS System | 2025-02-13 |
| FR-002 | Case/Bulk Pricing | 2025-02-13 |
| FR-003 | Age Verification Flow | 2025-02-13 |
