import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.database import Base, engine
from backend.seed_data import seed_database

# Import routers
from backend.api.auth_router import router as auth_router
from backend.api.inventory_router import router as inventory_router
from backend.api.operations_router import router as operations_router
from backend.api.intelligence_router import router as intelligence_router
from backend.api.advanced_router import router as advanced_router
from backend.api.dashboard_router import router as dashboard_router
from backend.api.digital_twin_router import router as digital_twin_router
from backend.api.assistant_router import router as assistant_router
from backend.api.ledger_router import router as ledger_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created and seeded
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Warehouse Inventory Management System with AI Intelligence and Trust Governance",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api/v1
api_prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=api_prefix)
app.include_router(inventory_router, prefix=api_prefix)
app.include_router(operations_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(intelligence_router, prefix=api_prefix)
app.include_router(advanced_router, prefix=api_prefix)
app.include_router(digital_twin_router, prefix=api_prefix)
app.include_router(assistant_router, prefix=api_prefix)
app.include_router(ledger_router, prefix=api_prefix)

# Serve Frontend static assets
frontend_dir = settings.FRONTEND_DIR
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"status": "StockSense API running", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
