# StockSense — Intelligent Multi-Warehouse Inventory Management System

StockSense is an enterprise-grade, modular inventory management system (IMS) engineered with **Python**, **FastAPI**, **SQLAlchemy 2.0**, **Pydantic v2**, and modern web standards. It digitizes physical warehouse operations, guarantees tamper-proof audit governance via a cryptographic trust chain, and provides decision intelligence via predictive machine learning, real-time spatial digital twins, and grounded AI assistance.

---

## 🏗️ Architecture & Core Components

```text
StockSense Architecture
├── Frontend (Vanilla ES6, HTML5 Canvas 2D Digital Twin, Odoo Enterprise Theme)
├── REST API Layer (FastAPI Routers: Auth, Products, Operations, Advanced, AI, Twin, Assistant)
├── Core Inventory Engine (Transactional, Atomically Balanced, Ledger-Audited)
├── Cryptographic Trust Chain (SHA-256 Hash Chaining, Merkle Trees)
├── AI Intelligence Engine (Forecasting, Dynamic Reorder, Anomalies, What-if)
└── 5 Advanced Modules:
    ├── 1. Dead-Stock Rescue (Scoring, Classification, Human-Confirmed Actions)
    ├── 2. Supplier Intelligence (Lead Times, Reliability Scores, Reorder Integration)
    ├── 3. Expiry / FEFO Management (Batch Tracking, 7d/30d Alerts, FEFO Pick Planner)
    ├── 4. Smart Picking Route (TSP Route Optimization, Time Saved, Twin Overlay)
    └── 5. Impact Score (0-100 Measurable Score across Forecasts, Reorders, & Anomalies)
```

---

## 🌟 25 Core Features Supported

### Core Operational Features
1. **Authentication & RBAC**: Roles for `ADMIN`, `INVENTORY_MANAGER`, and `WAREHOUSE_STAFF` with JWT security.
2. **Products & SKU**: Full product master data with SKUs, barcodes, categories, and UOM.
3. **Categories**: Multi-tier categorization of inventory materials and equipment.
4. **Warehouses**: Multi-warehouse support with capacity tracking and address records.
5. **Locations & Racks**: Spatial coordinates `(x, y, z)` for aisles, racks, and bins enabling 2D/3D navigation.
6. **Receipts (Incoming)**: Vendor purchase receipts with inspection, damage tracking, and automatic stock updates.
7. **Deliveries (Outgoing)**: Customer order dispatch, picking, packing, and automatic stock deduction.
8. **Internal Transfers**: Inter-warehouse and intra-warehouse transfers with dual-entry ledger logging.
9. **Stock Adjustments**: Physical inventory reconciliation with variance classifications (Damage, Theft, Expiry, Error).
10. **Stock Ledger**: Immutable historical journal of all stock movements with running balances.
11. **Dashboard**: Executive landing page snapshot with real-time KPIs and dynamic filtering.
12. **Search**: Instant search across SKU, product title, barcode, and categories.
13. **Alerts**: Automated alerts for low stock, out of stock, and critical expiry.
14. **Reports**: Inventory valuation and transaction turnover reporting.
15. **RBAC Security**: Role-based access controls for operational integrity.
16. **QR / Barcode Tracking**: SKU and barcode association for handheld terminal scanning.
17. **Audit Trail**: Detailed change history logging who performed what action, when, and from where.

### AI Intelligence Features
18. **Demand Forecasting**: 30-day forward demand projections with 95% Gaussian confidence intervals and weekly cyclicality.
19. **Dynamic Reorder**: Dynamic safety stock and Economic Order Quantity (EOQ) calculations.
20. **Explainability**: Clear mathematical and contextual explanations for all AI outputs.
21. **Confidence Score**: Statistical confidence percentages for every forecast and recommendation.
22. **Anomaly Detection**: Rolling Z-score spike detection and inventory shrinkage alerts.
23. **Cause-of-Loss**: Categorization of variance losses with actionable mitigation strategies.
24. **What-if Simulator**: Interactive simulation of demand shocks, lead-time delays, and reliability degradation.

### Showcase Features
25. **Digital Twin**: 2D interactive spatial warehouse map displaying rack heatmaps, occupancy, and status overlays.
26. **Cryptographic Trust Chain**: SHA-256 block hash-chaining preventing tampering of historical ledger logs.
27. **AI Inventory Assistant**: Natural-language conversational assistant grounded in live database queries.

---

## 🚀 5 New Advanced Features

### 1. Dead-Stock Rescue (`/api/v1/advanced/dead-stock`)
- **Intelligence**: Analyzes days since last movement, stock value, stock-to-demand ratio, and turnover.
- **Scoring**: Computes a 0–100 **Dead Stock Score** and classifies products into:
  * `Normal`
  * `Slow Moving`
  * `Excess Stock`
  * `Dead Stock`
- **Recommendations**: Proposes targeted rescue strategies (transfer to active warehouse, reduce reorder point, stop purchasing, RMA supplier return, or promotional clearance).
- **Safety**: **Zero automatic modifications** — all actions require explicit user confirmation through an authorized confirmation modal.

### 2. Supplier Intelligence (`/api/v1/advanced/suppliers`)
- **Tracking**: Continuously tracks actual lead time, expected lead time, on-time delivery %, quantity accuracy %, damage rate %, and purchase frequency from receipt logs.
- **Supplier Reliability Score**: Composite 0–100 rating based on historical vendor performance.
- **AI Integration**: Directly feeds vendor reliability and lead-time variance into the **Dynamic Reorder Engine** and **What-if Simulator**.

### 3. Expiry / FEFO Management (`/api/v1/advanced/expiry`, `/api/v1/advanced/fefo`)
- **Batch Tracking**: Tracks batch number, manufacturing date, expiration date, quantity, warehouse, and rack location.
- **FEFO Engine**: Implements *First Expired, First Out* algorithm prioritizing batches with earliest expiry dates first.
- **Alerts**: Expiry alerts for expired batches, critical batches (< 7 days), and warning batches (< 30 days).

### 4. Smart Picking Route (`/api/v1/advanced/picking-route`)
- **Optimization**: Computes optimal Traveling Salesperson Problem (TSP) picking paths using rack spatial coordinates $(x, y, z)$ with Nearest Neighbor + 2-Opt heuristic.
- **Metrics**: Computes total distance, original distance, estimated picking time, and time saved.
- **Digital Twin Visualization**: Draws the animated sequential walk path live on the warehouse canvas.
- **Worker Confirmation**: Step-by-step checklist requiring manual verification of each pick.

### 5. Impact Score (`/api/v1/intelligence/impact`)
- **0–100 Decision Priority Score**: Evaluated mathematically from:
  1. Stockout Risk (0–100)
  2. Financial Exposure (in INR)
  3. Demand Volatility (Coefficient of Variation)
  4. Lead Time Length
  5. Supplier Reliability Risk
- **Integrated Across**: Forecasting, Dynamic Reorders, Anomalies, What-if, and Dead-Stock Rescue with clear bulleted reasons.

---

## 🛠️ Installation & Running

### Requirements
- Python 3.11+
- Pip packages in `requirements.txt`

### 1. Run Automated Test Suite
```powershell
python -m pytest -v
```
All 20 unit and integration tests will execute and pass, verifying both core operations and all 5 new advanced features.

### 2. Launch Application
```powershell
python run.py
```
Open your browser at:
👉 **http://127.0.0.1:8000**

Interactive API documentation available at:
👉 **http://127.0.0.1:8000/docs**
