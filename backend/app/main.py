from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.database import engine, Base
import app.models # ensure all models are registered

# API Router Imports
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.warehouses import router as warehouses_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.deliveries import router as deliveries_router
from app.api.v1.transfers import router as transfers_router
from app.api.v1.adjustments import router as adjustments_router
from app.api.v1.ledger import router as ledger_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.search import router as search_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.reports import router as reports_router
from app.api.v1.roles import router as roles_router
from app.api.v1.qr import router as qr_router
from app.api.v1.audit import router as audit_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.showcase import router as showcase_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite / PostgreSQL tables
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
# StockSense - Enterprise & Intelligent Inventory Management System (IMS)

A modular, real-time inventory management backend built on Odoo-style double-entry stock keeping with AI intelligence and blockchain auditing.

### 🌟 25 Supported Capabilities:
1. **Core (15)**: Login & OTP, Products, Warehouses & Racks, Receipts, Deliveries, Transfers, Adjustments, Stock Ledger, Dashboard KPIs, Search, Alerts, Reports, Roles RBAC, QR Engine, Audit Trail.
2. **Intelligent (7)**: Forecasting, Dynamic Reorder ROP/EOQ, Explainability XAI, Confidence Scoring, Anomaly Detection, Cause-of-Loss, What-If Simulator.
3. **Showcase (3)**: Digital Twin 3D/Heatmaps, Trust Chain Cryptographic Immutability, AI Copilot Assistant.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
v1 = settings.API_V1_STR
app.include_router(auth_router, prefix=v1)
app.include_router(products_router, prefix=v1)
app.include_router(warehouses_router, prefix=v1)
app.include_router(receipts_router, prefix=v1)
app.include_router(deliveries_router, prefix=v1)
app.include_router(transfers_router, prefix=v1)
app.include_router(adjustments_router, prefix=v1)
app.include_router(ledger_router, prefix=v1)
app.include_router(dashboard_router, prefix=v1)
app.include_router(search_router, prefix=v1)
app.include_router(alerts_router, prefix=v1)
app.include_router(reports_router, prefix=v1)
app.include_router(roles_router, prefix=v1)
app.include_router(qr_router, prefix=v1)
app.include_router(audit_router, prefix=v1)
app.include_router(intelligence_router, prefix=v1)
app.include_router(showcase_router, prefix=v1)

# Static files mounting
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "ui_app": "/app",
        "swagger_docs": "/docs",
        "features_total": 25,
        "modules": {
            "core": 15,
            "intelligent": 7,
            "showcase": 3
        }
    }

@app.get("/app", tags=["Frontend"])
@app.get("/", tags=["Frontend"])
def serve_frontend_ui():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return health_check()

