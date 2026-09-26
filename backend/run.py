import uvicorn
from seed_data import run_seed

if __name__ == "__main__":
    print("Running initial database migrations & seeding...")
    run_seed()
    print("\n" + "="*70)
    print("🚀 StockSense Backend Server Starting...")
    print("📍 API Base URL:       http://127.0.0.1:8000")
    print("📖 Swagger UI Docs:    http://127.0.0.1:8000/docs")
    print("📑 ReDoc Specs:        http://127.0.0.1:8000/redoc")
    print("="*70 + "\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
