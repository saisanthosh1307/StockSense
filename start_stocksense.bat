@echo off
title StockSense - Enterprise Inventory Management System
echo =========================================================================
echo               🚀 Launching StockSense IMS (Full Stack)
echo =========================================================================
echo.

cd /d "%~dp0backend"
echo [1/2] Initializing Database & Verifying Migrations...
python seed_data.py

echo.
echo [2/2] Starting StockSense Web Application & API Server on http://127.0.0.1:8000 ...
echo - Web Application UI:  http://127.0.0.1:8000
echo - Swagger API Docs:    http://127.0.0.1:8000/docs
echo - Alternative ReDoc:   http://127.0.0.1:8000/redoc
echo =========================================================================
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
