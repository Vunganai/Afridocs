# AfriDocs AI

> AI-powered Invoice Processing Platform for African businesses.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + shadcn/ui + Tailwind |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Database | Supabase (PostgreSQL + Row Level Security) |
| Auth | Supabase Auth (JWT + Google OAuth) |
| Queue | Celery + Redis |
| OCR | Azure AI Document Intelligence (prebuilt-invoice) |
| LLM | Azure OpenAI GPT-4o |
| Storage | Azure Blob Storage (local disk in dev) |
| Deploy | Docker Compose (dev) → Azure Container Apps (pilot) |
| CI/CD | GitHub Actions |

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd afridocs
cp .env.example .env          # fill in your values
cp frontend/.env.local.example frontend/.env.local
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (dev only) | http://localhost:8000/docs |
| Redis | localhost:6379 |

### 3. Run database migrations

```bash
# Against your Supabase DB
docker compose exec api alembic upgrade head
```

### 4. Local dev (without Docker)

```bash
# Backend
cd backend
pip install uv
uv pip install -e ".[dev]"
uvicorn app.main:app --reload

# Worker (separate terminal)
celery -A app.worker.celery_app worker --loglevel=info -Q documents

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

```
afridocs/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # FastAPI route handlers
│   │   ├── core/               # Config, security, logging, exceptions
│   │   ├── db/                 # SQLAlchemy engine + session
│   │   ├── models/             # ORM models (Tenant, User, Document, ...)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # AI services, storage, audit
│   │   └── worker/             # Celery app + tasks
│   ├── alembic/                # DB migrations
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── components/         # UI components + layout
│       ├── hooks/              # useAuth, useToast
│       ├── lib/                # Supabase client, Axios client, utils
│       ├── pages/              # Auth, Dashboard, Upload, Documents, Review
│       ├── stores/             # Zustand auth store
│       └── types/              # TypeScript type definitions
│
├── docs/                       # Phase documentation
├── docker-compose.yml
├── .env.example
└── Makefile
```

## MVP Invoice Processing Flow

```
User uploads PDF
      ↓
FastAPI validates (MIME, size, hash dedup)
      ↓
Celery task queued
      ↓
Azure Document Intelligence → extract fields
      ↓
GPT-4o → classify + gap-fill low-confidence fields
      ↓
Validator → check business rules
      ↓
≥95% confidence + no errors → EXTRACTED (approval queue)
< 80% confidence or errors  → REVIEW_REQUIRED (human queue)
      ↓
Reviewer approves/corrects → APPROVED
```

## Environment Variables

See `.env.example` for the full list. Required before first run:

- `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_JWT_SECRET`
- `DATABASE_URL` (Supabase connection string)
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` + `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_KEY` + `AZURE_OPENAI_DEPLOYMENT_NAME`

## CI/CD

- **CI** (every PR and `main`): lint and tests — `.github/workflows/ci.yml`
- **CD** (after CI succeeds on `main`): push images to GitHub Container Registry — `.github/workflows/cd.yml`

How to pull those images and run them: **[docs/deploy-v1.md](docs/deploy-v1.md)**. Local development still uses `docker compose up --build`.

## Makefile Commands

```bash
make up           # Start all Docker services
make down         # Stop all services
make migrate      # Run Alembic migrations
make test         # Run all tests
make lint         # Lint backend + frontend
```
