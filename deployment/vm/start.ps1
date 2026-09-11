# MedAI – Quick Start Script
# Run this from the project root: .\start.ps1

Write-Host "`n🚀 Starting MedAI..." -ForegroundColor Cyan

# 1. Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# 2. Start Docker services (Postgres, Redis, Qdrant)
Write-Host "`n🐳 Starting Docker services..." -ForegroundColor Yellow
docker compose up -d

# 3. Wait for Postgres to be ready
Write-Host "`n⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 4. Start FastAPI dev server
Write-Host "`n🌐 Starting FastAPI server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "   📖 API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "   📘 ReDoc:    http://localhost:8000/redoc`n" -ForegroundColor Green

uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
