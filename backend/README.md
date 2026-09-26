# StockSense - Modular & Intelligent Inventory Management System (IMS)

StockSense is an enterprise-grade, Odoo-inspired Inventory Management System designed to replace manual registers, Excel spreadsheets, and scattered tracking methods with a centralized, real-time backend.

Built using **Python (FastAPI + SQLAlchemy 2.0 + Pydantic v2)**, it delivers a strict double-entry stock movement engine, 7 intelligent forecasting and loss prevention algorithms, and 3 showcase features including a 3D/Heatmap Digital Twin, Cryptographic Trust Chain, and Natural Language AI Assistant.

---

## 🏗️ Architecture & Language Selection Rationale

### Why Python (FastAPI) is the Optimal Choice for StockSense
1. **Unified AI/ML & Enterprise Ecosystem**: 7 of the requested features require predictive mathematics (Holt-Winters double exponential smoothing, statistical Z-score/IQR anomaly detection, Monte Carlo stress-testing, and dynamic EOQ/safety stock optimization). Python (`numpy`, `scipy`, `scikit-learn`) executes these natively in-process without requiring secondary microservices.
2. **Odoo's Proven Inventory Model**: Odoo itself is built in Python. StockSense utilizes Odoo's battle-tested **Double-Entry Stock Ledger** (`from_location -> to_location`), where stock is never updated arbitrarily; every change is an immutable transaction.
3. **High Async Throughput**: FastAPI runs on ASGI (Starlette + Uvicorn), delivering I/O performance on par with Go and Node.js while automatically generating interactive Swagger/OpenAPI documentation.

---

## 🌟 Complete 25-Feature Coverage

### Core Operations (15 Features)
| # | Feature | Endpoint | Description |
|---|---|---|---|
| 1 | **Login & Auth** | `POST /api/v1/auth/login`, `POST /api/v1/auth/request-otp` | JWT authentication + OTP-based password reset simulation |
| 2 | **Products** | `POST /api/v1/products`, `GET /api/v1/products` | CRUD products with SKU, UoM, barcode, unit cost/price, min/max rules, and location stock breakdown |
| 3 | **Warehouses** | `POST /api/v1/warehouses`, `GET /api/v1/warehouses/locations` | Multi-warehouse support with zones, aisles, racks, and shelves |
| 4 | **Receipts** | `POST /api/v1/receipts`, `POST /api/v1/receipts/{id}/validate` | Incoming stock from vendors; validation automatically increases stock |
| 5 | **Deliveries** | `POST /api/v1/deliveries`, `/pick`, `/pack`, `/validate` | Outgoing goods for customer orders with pick/pack workflows; validation decreases stock |
| 6 | **Transfers** | `POST /api/v1/transfers`, `POST /api/v1/transfers/{id}/validate` | Internal stock moves (Main Store -> Production Floor, Rack A -> Rack B); updates location without changing total count |
| 7 | **Adjustments** | `POST /api/v1/adjustments`, `POST /api/v1/adjustments/{id}/validate` | Reconciles physical counts against recorded stock, auto-moving discrepancy to Loss/Scrap |
| 8 | **Stock Ledger** | `GET /api/v1/ledger` | Immutable double-entry transaction history with cryptographic signatures |
| 9 | **Dashboard** | `GET /api/v1/dashboard/kpis`, `/operations-feed` | Real-time KPIs (Total products, low stock, pending receipts/deliveries, scheduled transfers) with dynamic filters |
| 10 | **Search** | `GET /api/v1/search?q={query}` | High-speed search across SKU, Barcode, Product Name, and Warehouse Racks |
| 11 | **Alerts** | `GET /api/v1/alerts`, `POST /api/v1/alerts/scan` | Proactive low stock alerts and notification management |
| 12 | **Reports** | `GET /api/v1/reports/valuation`, `/turnover`, `/export/csv` | Financial valuation, inventory turnover velocity (A/B/C), and CSV export |
| 13 | **Roles & RBAC** | `GET /api/v1/roles/permissions`, `GET /api/v1/roles/users` | Granular role-based access control (Admin, Inventory Manager, Warehouse Staff) |
| 14 | **QR Engine** | `GET /api/v1/qr/product/{id}`, `POST /api/v1/qr/scan` | Base64 PNG QR code generation and mobile camera scanning resolution |
| 15 | **Audit Trail** | `GET /api/v1/audit/logs` | Immutable audit log capturing user actions, timestamps, and entity changes |

---

### Intelligent Engine (7 Features)
| # | Feature | Endpoint | Description |
|---|---|---|---|
| 16 | **Forecasting** | `GET /api/v1/intelligence/forecast/{product_id}` | Time-series demand forecasting using Holt's Linear Trend with 95% Confidence Intervals |
| 17 | **Dynamic Reorder** | `GET /api/v1/intelligence/reorder/{product_id}` | Dynamic Reorder Point $ROP = (d \times L) + SS$ and Economic Order Quantity (EOQ) |
| 18 | **Explainability (XAI)** | `GET /api/v1/intelligence/explainability/{product_id}` | Plain-English and mathematical decomposition of why replenishment is triggered |
| 19 | **Confidence Score** | `GET /api/v1/intelligence/confidence/{product_id}` | Statistical accuracy rating (0-100%) based on demand variance, MAPE, and data depth |
| 20 | **Anomaly Detection** | `GET /api/v1/intelligence/anomalies` | Statistical Z-score and IQR analysis flagging abnormal consumption spikes and shrinkage |
| 21 | **Cause-of-Loss** | `GET /api/v1/intelligence/cause-of-loss` | Root-cause breakdown of write-offs (Damage, Spoilage, Theft, Transit) with actionable mitigation strategies |
| 22 | **What-If Simulator** | `POST /api/v1/intelligence/what-if` | Stress-test engine simulating demand surges (+35%) and supplier delays (+7 days) to calculate stockout day and required buffer |

---

### Showcase Innovations (3 Features)
| # | Feature | Endpoint | Description |
|---|---|---|---|
| 23 | **Digital Twin** | `GET /api/v1/showcase/digital-twin/{warehouse_id}` | Virtual 2D/3D warehouse mapping, rack slot capacity utilization, and pick frequency heatmaps |
| 24 | **Trust Chain** | `GET /api/v1/showcase/trust-chain/blocks`, `/verify` | SHA-256 Merkle-linked blockchain sealing stock moves; detects database tampering |
| 25 | **AI Assistant** | `POST /api/v1/showcase/ai-assistant/chat` | Natural Language conversational copilot answering operational queries and executing actions |

---

## 🚀 Getting Started

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Run Database Seeding & Launch Server
```bash
python run.py
```

The server will launch at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Alternative ReDoc**: `http://127.0.0.1:8000/redoc`

### 3. Run Automated 25-Feature Test Suite
```bash
python test_backend.py
```

---

## 🔐 Default Demo Credentials
- **Admin**: `admin@stocksense.com` / `admin123`
- **Inventory Manager**: `manager@stocksense.com` / `manager123`
- **Warehouse Staff**: `staff@stocksense.com` / `staff123`
