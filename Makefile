# ============================================================
#  AfriDocs AI — Makefile
#  Common development commands.
#  Requires: make, docker, python 3.12+, node 20+
# ============================================================

.PHONY: help up down build logs api worker frontend \
        install-backend install-frontend \
        migrate migrate-create lint test \
        clean

# Default target
help:
	@echo ""
	@echo "AfriDocs AI — Available Commands"
	@echo "─────────────────────────────────────────────────────"
	@echo "  make up              Start all services (docker compose)"
	@echo "  make down            Stop all services"
	@echo "  make build           Rebuild all images"
	@echo "  make logs            Tail all logs"
	@echo ""
	@echo "  make api             Start backend only (local, no docker)"
	@echo "  make worker          Start Celery worker (local, no docker)"
	@echo "  make frontend        Start Vite dev server (local, no docker)"
	@echo ""
	@echo "  make install-backend    Install Python deps (uv)"
	@echo "  make install-frontend   Install Node deps"
	@echo ""
	@echo "  make migrate            Run Alembic migrations"
	@echo "  make migrate-create m=\"description\"  Create new migration"
	@echo ""
	@echo "  make lint            Lint backend (ruff) + frontend (eslint)"
	@echo "  make test            Run all tests"
	@echo "  make clean           Remove build artefacts"
	@echo ""

# ── Docker ────────────────────────────────────────────────────
up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ── Local (no docker) ─────────────────────────────────────────
api:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	cd backend && celery -A app.worker.celery_app worker --loglevel=info --concurrency=2 -Q documents

beat:
	cd backend && celery -A app.worker.celery_app beat --loglevel=info

frontend:
	cd frontend && npm run dev

# ── Install ───────────────────────────────────────────────────
install-backend:
	cd backend && pip install uv && uv pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

install: install-backend install-frontend

# ── Database ──────────────────────────────────────────────────
migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(m)"

migrate-down:
	cd backend && alembic downgrade -1

# ── Quality ───────────────────────────────────────────────────
lint-backend:
	cd backend && ruff check . && ruff format --check .

lint-frontend:
	cd frontend && npm run lint

lint: lint-backend lint-frontend

format-backend:
	cd backend && ruff format .

test-backend:
	cd backend && pytest -v --tb=short

test-frontend:
	cd frontend && npm run test -- --run

test: test-backend test-frontend

# ── Clean ─────────────────────────────────────────────────────
clean:
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/htmlcov
	rm -rf frontend/dist frontend/.vite
