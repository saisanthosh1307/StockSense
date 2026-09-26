Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "              🚀 Launching StockSense IMS (Full Stack)" -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan

$backendPath = Join-Path $PSScriptRoot "backend"
Set-Location -Path $backendPath

Write-Host "`n[1/2] Initializing Database & Verifying Migrations..." -ForegroundColor Yellow
python seed_data.py

Write-Host "`n[2/2] Starting StockSense Web Application & API Server..." -ForegroundColor Yellow
Write-Host "- Web Application UI:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "- Swagger API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "- Alternative ReDoc:   http://127.0.0.1:8000/redoc" -ForegroundColor Cyan
Write-Host "=========================================================================`n" -ForegroundColor Cyan

Start-Process "http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
