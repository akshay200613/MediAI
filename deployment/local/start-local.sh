#!/usr/bin/env bash
# =============================================================================
# MedAI – Local Development Startup Script (Linux / macOS / WSL)
# Usage: ./start-local.sh
# =============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
RESET='\033[0m'

echo ""
echo -e "  ${CYAN}MedAI Local Dev Stack${RESET}"
echo -e "  ${GRAY}─────────────────────────────────────────────${RESET}"
echo ""

# Step 1: Bootstrap .env.local
if [ ! -f ".env.local" ]; then
    if [ -f ".env.local.example" ]; then
        cp .env.local.example .env.local
        echo -e "  ${GREEN}[1/3] Created .env.local from .env.local.example${RESET}"
        echo ""
        echo -e "  ${YELLOW}⚠  ACTION REQUIRED: Open .env.local and fill in your API keys:${RESET}"
        echo -e "  ${YELLOW}     - GEMINI_API_KEY   → https://aistudio.google.com/app/apikey${RESET}"
        echo -e "  ${YELLOW}     - GROQ_API_KEY     → https://console.groq.com${RESET}"
        echo ""
        read -r -p "  Press Enter to continue once keys are filled in, or Ctrl+C to cancel..."
    else
        echo -e "  ${RED}[ERROR] .env.local.example not found.${RESET}"
        exit 1
    fi
else
    echo -e "  ${GRAY}[1/3] .env.local already exists — skipping${RESET}"
fi

# Step 2: Build and start
echo -e "  ${CYAN}[2/3] Starting Docker stack (this may take a few minutes on first run)...${RESET}"
docker compose -f deployment/local/docker-compose.local.yml up -d --build

# Step 3: Wait for API health check
echo -e "  ${CYAN}[3/3] Waiting for API to become healthy...${RESET}"
RETRIES=24
HEALTHY=false

for i in $(seq 1 $RETRIES); do
    sleep 5
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health/live 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        HEALTHY=true
        break
    else
        echo -e "  ${GRAY}... still starting (${i}0s elapsed)${RESET}"
    fi
done

echo ""
if [ "$HEALTHY" = true ]; then
    echo -e "  ${GREEN}✅  MedAI is running!${RESET}"
else
    echo -e "  ${YELLOW}⚠  API health check timed out. Services may still be starting.${RESET}"
    echo -e "  ${YELLOW}   Run: docker compose -f deployment/local/docker-compose.local.yml logs api${RESET}"
fi

echo ""
echo -e "  ${CYAN}Access URLs:${RESET}"
echo -e "    Frontend  →  http://localhost:3000"
echo -e "    API       →  http://localhost:8000"
echo -e "    API Docs  →  http://localhost:8000/docs"
echo -e "    Qdrant    →  http://localhost:6333/dashboard"
echo ""
echo -e "  ${CYAN}Useful commands:${RESET}"
echo -e "  ${GRAY}  Logs     →  docker compose -f deployment/local/docker-compose.local.yml logs -f${RESET}"
echo -e "  ${GRAY}  Stop     →  docker compose -f deployment/local/docker-compose.local.yml down${RESET}"
echo -e "  ${GRAY}  Rebuild  →  docker compose -f deployment/local/docker-compose.local.yml up -d --build${RESET}"
echo ""
