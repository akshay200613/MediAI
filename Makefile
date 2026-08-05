# =============================================================================
# MedAI – Developer Makefile
# Usage: make <target>
# =============================================================================

.PHONY: help install dev test lint format typecheck migrate clean

# ── Colors ────────────────────────────────────────────────────────────────────
CYAN  := \033[0;36m
RESET := \033[0m

help: ## Show this help message
	@echo ""
	@echo "  $(CYAN)MedAI$(RESET) — Developer Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────
install: ## Install all Python dependencies with uv
	pip install uv
	uv sync --all-extras

install-frontend: ## Install frontend dependencies
	cd apps/frontend && npm install

setup: install install-frontend ## Full setup (Python + Node)
	cp -n .env.example .env.local || true
	@echo "✅ Setup complete. Edit .env.local with your credentials."

# ── Development ───────────────────────────────────────────────────────────────
dev: ## Start FastAPI dev server
	uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Start Next.js dev server
	cd apps/frontend && npm run dev

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new name="add_patients_table")
	alembic revision --autogenerate -m "$(name)"

migrate-down: ## Rollback last migration
	alembic downgrade -1

# ── Docker (Infrastructure) ──────────────────────────────────────────────────
docker-up: ## Start PostgreSQL, Redis, and Qdrant
	docker compose up -d

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## Tail Docker logs
	docker compose logs -f

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run all tests with coverage
	pytest tests/ -v --cov=core --cov=domains --cov=apps --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

# ── Code Quality ──────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	ruff check core/ domains/ apps/

format: ## Format code with ruff
	ruff format core/ domains/ apps/

typecheck: ## Run mypy type checks
	mypy core/ domains/ apps/

check: lint typecheck ## Run all code quality checks

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Clean Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	rm -rf .pytest_cache htmlcov .mypy_cache .ruff_cache

# ── Docs ─────────────────────────────────────────────────────────────────────
docs-serve: ## Serve API docs (requires running server)
	@echo "API Docs: http://localhost:8000/docs"
	@echo "ReDoc:    http://localhost:8000/redoc"
