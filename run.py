import uvicorn
from backend.seed_data import seed_database

if __name__ == "__main__":
    print("Starting StockSense Inventory Management System v2.0...")
    seed_database()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
