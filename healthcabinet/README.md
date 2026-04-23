# HealthCabinet

Personal health data management platform. Securely stores, processes, and interprets health documents using AI.

## Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd healthcabinet
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit both .env files with your values
```

### 2. Generate encryption key

```bash
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
# Add output as ENCRYPTION_KEY in backend/.env
```

### 3. Run with Docker Compose

```bash
docker compose up -d
```

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 5. Verify

```bash
curl http://localhost:8000/health   # {"status": "ok"}
open http://localhost:3000          # SvelteKit frontend
```

## Development

### Backend (FastAPI)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend (SvelteKit)

```bash
cd frontend
npm install
npm run dev
```

### Run tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm run test:unit
```

## Structure

```
healthcabinet/
├── frontend/           # SvelteKit 2 + Svelte 5 app
├── backend/            # FastAPI + SQLAlchemy async
├── k8s/               # Kubernetes manifests (Kustomize)
└── .github/workflows/  # CI/CD pipelines
```

## Tech Stack

- **Frontend**: SvelteKit 2, Svelte 5 (runes), Tailwind CSS v4, shadcn-svelte, TanStack Query
- **Backend**: FastAPI 0.135+, SQLAlchemy 2.0 async, Alembic, ARQ (Redis jobs)
- **Database**: PostgreSQL 16
- **Infrastructure**: AWS eu-central-1, EKS, FluxCD, SOPS secrets

## Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| UX Design System | `_bmad-output/planning-artifacts/ux-design-specification.md` | Colors, typography, components, user journeys, accessibility |
| UX Page Specs | `_bmad-output/planning-artifacts/ux-page-specifications.md` | Per-page wireframes, states, component specs for developers |
| Visual Mockups | `_bmad-output/planning-artifacts/ux-page-mockups.html` | Open in browser — interactive page mockups with real design tokens |
| Design Directions | `_bmad-output/planning-artifacts/ux-design-directions.html` | Interactive design direction showcase |
| PRD | `_bmad-output/planning-artifacts/prd.md` | Product requirements (FR1–FR38) |
| Architecture | `_bmad-output/planning-artifacts/architecture.md` | Technical architecture decisions |
| Epics | `_bmad-output/planning-artifacts/epics.md` | Epic/story breakdown |
