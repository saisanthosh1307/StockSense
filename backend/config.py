import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "StockSense Inventory Management System"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "stocksense-super-secret-production-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # SQLite default database path
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'stocksense.db'}")
    
    # Frontend directory
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    
    # Business logic defaults
    DEAD_STOCK_DAYS_THRESHOLD: int = 60
    FEFO_EXPIRING_SOON_DAYS: int = 30
    FEFO_CRITICAL_DAYS: int = 7
    CURRENCY_SYMBOL: str = "₹"

settings = Settings()
