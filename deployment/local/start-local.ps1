# =============================================================================
# MedAI – Local Development Startup Script (Windows PowerShell)
# Usage: .\start-local.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  MedAI Local Dev Stack" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# Step 1: Bootstrap .env.local
if (-not (Test-Path ".env.local")) {
    if (Test-Path ".env.local.example") {
        Copy-Item ".env.local.example" ".env.local"
        Write-Host "  [1/3] Created .env.local from .env.local.example" -ForegroundColor Green
        Write-Host ""
        Write-Host "  ⚠  ACTION REQUIRED: Open .env.local and fill in your API keys:" -ForegroundColor Yellow
        Write-Host "     - GEMINI_API_KEY   → https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
        Write-Host "     - GROQ_API_KEY     → https://console.groq.com" -ForegroundColor Yellow
        Write-Host ""
        $continue = Read-Host "  Press Enter to continue once keys are filled in, or Ctrl+C to cancel"
    } else {
        Write-Host "  [ERROR] .env.local.example not found. Cannot create .env.local" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [1/3] .env.local already exists — skipping" -ForegroundColor DarkGray
}

# Step 2: Build and start containers
Write-Host "  [2/3] Starting Docker stack (this may take a few minutes on first run)..." -ForegroundColor Cyan
docker compose -f deployment\local\docker-compose.local.yml up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Docker Compose failed. Check the output above." -ForegroundColor Red
    exit 1
}

# Step 3: Wait for API health check
Write-Host "  [3/3] Waiting for API to become healthy..." -ForegroundColor Cyan
$retries = 24
$healthy = $false

for ($i = 0; $i -lt $retries; $i++) {
    Start-Sleep -Seconds 5
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/live" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        Write-Host "  ... still starting ($([int](($i+1)*5))s elapsed)" -ForegroundColor DarkGray
    }
}

Write-Host ""
if ($healthy) {
    Write-Host "  ✅  MedAI is running!" -ForegroundColor Green
} else {
    Write-Host "  ⚠  API health check timed out. Services may still be starting." -ForegroundColor Yellow
    Write-Host "     Run: docker compose -f deployment\local\docker-compose.local.yml logs api" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Access URLs:" -ForegroundColor Cyan
Write-Host "    Frontend  →  http://localhost:3000" -ForegroundColor White
Write-Host "    API       →  http://localhost:8000" -ForegroundColor White
Write-Host "    API Docs  →  http://localhost:8000/docs" -ForegroundColor White
Write-Host "    Qdrant    →  http://localhost:6333/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor Cyan
Write-Host "    Logs     →  docker compose -f deployment\local\docker-compose.local.yml logs -f" -ForegroundColor DarkGray
Write-Host "    Stop     →  docker compose -f deployment\local\docker-compose.local.yml down" -ForegroundColor DarkGray
Write-Host "    Rebuild  →  docker compose -f deployment\local\docker-compose.local.yml up -d --build" -ForegroundColor DarkGray
Write-Host ""
