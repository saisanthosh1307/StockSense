# StockSense - Enterprise & Intelligent Inventory Management System (IMS)

StockSense is a production-ready, modular Inventory Management System built on Odoo's double-entry stock keeping principles, augmented with 7 intelligent predictive algorithms and 3 showcase innovations.

---

## 📁 Project Directory Structure

```text
C:\Users\G V Sai Santosh\.gemini\antigravity\scratch\stocksense\
├── start_stocksense.bat        # One-click Windows launcher
├── start_stocksense.ps1        # PowerShell launcher
├── README.md                   # System documentation
│
├── backend/                    # FastAPI + SQLAlchemy 2.0 + SQLite Backend
│   ├── app/
│   │   ├── config.py           # Application settings & JWT secret
│   │   ├── database.py         # SQLAlchemy engine & session dependency
│   │   ├── main.py             # FastAPI entry point, routers & static serving
│   │   ├── models/             # User, Inventory, Operations, Ledger, Audit, TrustChain
│   │   ├── schemas/            # Pydantic v2 validation schemas
│   │   ├── services/           # Double-entry ledger, Forecasting, QR, TrustChain, AI
│   │   ├── api/v1/             # 13 REST API router modules (all 25 features)
│   │   └── static/             # Embedded single-page application (HTML/JS/Tailwind)
│   ├── seed_data.py            # Database population matching PDF problem statement
│   ├── test_backend.py         # Automated 25-feature end-to-end verification test suite
│   ├── requirements.txt        # Backend dependencies
│   └── run.py                  # Python launcher script
│
└── frontend/                   # Standalone React 18 + Vite frontend
    ├── src/
    │   ├── App.jsx             # React SPA component
    │   ├── main.jsx            # Entry point
    │   └── services/api.js     # REST client
    ├── package.json            # Node dependencies
    ├── vite.config.js          # Vite config with backend proxy
    └── index.html              # HTML shell
```

---

## ⚡ Quick Start

### 1. Launch with One Click
Double-click `start_stocksense.bat` (or run `./start_stocksense.ps1` in PowerShell).

It will:
1. Initialize the SQLite database and seed demo items matching the PDF problem statement.
2. Launch the backend API and embedded frontend on `http://127.0.0.1:8000`.
3. Automatically open your browser to the StockSense web application.

### 2. Manual Launch
```powershell
cd "C:\Users\G V Sai Santosh\.gemini\antigravity\scratch\stocksense\backend"
python run.py
```

- **Web Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Run Automated Verification Tests
To run automated tests across all 25 features:
```powershell
cd "C:\Users\G V Sai Santosh\.gemini\antigravity\scratch\stocksense\backend"
python test_backend.py
```

---

## 🔑 Demo Login Accounts
- **Administrator**: `admin@stocksense.com` / `admin123` (Full system access)
- **Inventory Manager**: `manager@stocksense.com` / `manager123` (Receipts, Deliveries, Replenishment, Forecasting)
- **Warehouse Staff**: `staff@stocksense.com` / `staff123` (Picking, Packing, Internal Moves, Cycle Count Adjustments)
