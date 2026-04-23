# Copilot Instructions — HealthCabinet

This file provides guidance when working with code in this repository.

## Project Overview

**HealthCabinet** — a personal health data management platform that securely stores, processes, and interprets health documents using AI. Health data is strictly stored in AWS `eu-central-1`.

use Contex7 mcp to find dock ar web search.

## Repository Structure

```
healthcabinet/
├── frontend/       # SvelteKit 2 + Svelte 5 (runes), Tailwind CSS v4, TypeScript
├── backend/        # FastAPI, SQLAlchemy 2.0 async, Python 3.12
├── k8s/            # Kubernetes manifests (Kustomize overlays: dev/staging/prod)
└── docker-compose.yml
_bmad/              # BMad agent/workflow framework (separate from the app)
```

## Design & UX Documentation

All UX and design specifications live in `_bmad-output/planning-artifacts/`. **Read these before implementing any UI work:**

| Document | Purpose |
|----------|---------|
| **`ux-design-specification.md`** | Complete design system: color tokens, typography, spacing, custom component anatomy, user journeys, accessibility requirements, responsive breakpoints |
| **`ux-page-specifications.md`** | Page-by-page developer specs: wireframes, component breakdowns, states, validation rules, responsive behavior, implementation priority |
| **`ux-page-mockups.html`** | Interactive visual mockups — open in browser to see all pages with the dark-neutral theme, layout, and real design tokens |
| **`ux-design-directions.html`** | Six interactive design direction demos showing the unified aesthetic across screens |
| **`prd.md`** | Product Requirements Document — all functional requirements (FR1–FR38), user journeys, success criteria |
| **`epics.md`** | Epics and stories breakdown mapped to requirements |

### Key Design Decisions

- **Theme:** Dark-neutral precision palette (Bloomberg/Stripe inspired) — `surface-base: #0F1117`, `accent: #4F6EF7`
- **Health status colors:** Optimal (#2DD4A0), Borderline (#F5C842), Concerning (#F08430), Action (#E05252) — never color-only, always paired with text label
- **Layout:** Left sidebar (240px) on desktop, bottom tab bar on mobile (<768px)
- **Components:** shadcn-svelte themed to design tokens + custom health domain components
- **Font:** Inter, type scale from 11px (micro) to 32px (display)

## Development Commands

### Local Setup (Docker Compose)

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

Backend: `http://localhost:8000` | Frontend: `http://localhost:3000`

### Backend (FastAPI)

```bash
cd healthcabinet/backend
uv sync                                              # Install dependencies
uv run uvicorn app.main:app --reload --port 8000     # Dev server
uv run pytest                                        # All tests
uv run pytest tests/path/to/test_file.py::test_name  # Single test
uv run ruff check .                                  # Lint
uv run ruff format .                                 # Format
uv run mypy app/                                     # Type check
uv run alembic upgrade head                          # Run migrations
uv run alembic revision --autogenerate -m "desc"     # New migration
```

### Frontend (SvelteKit)

```bash
cd healthcabinet/frontend
npm install
npm run dev          # Dev server
npm run build        # Production build
npm run check        # Svelte type check
npm run lint         # ESLint + Prettier check
npm run format       # Auto-format
npm run test:unit    # Vitest unit tests
npm run test:e2e -- --project=chromium  # Playwright E2E tests
```

## Architecture

### Backend (`healthcabinet/backend/app/`)

- **`main.py`** — FastAPI app setup: CORS, middleware, RFC 7807 exception handlers, health endpoint. Domain routers are registered here (most are stubbed pending future epics).
- **`core/`** — Shared infrastructure: `config.py` (Pydantic Settings), `database.py` (async SQLAlchemy sessions), `security.py` (password hashing, JWT via PyJWT), `encryption.py`, `middleware.py` (request ID tracking), `rate_limit.py` (per-email + per-IP via Redis).
- **`auth/`** — Authentication: JWT access tokens (15-min) + refresh tokens (30-day HTTP-only cookies). Email is normalized to lowercase on creation.
- **`users/`** — User model: UUID id, email (unique), hashed_password, role (user/admin), tier (free/paid), timestamps.
- **Domain modules** (`documents/`, `processing/`, `health_data/`, `ai/`, `billing/`, `admin/`) — Currently stubbed; will be implemented in future epics.

**Key patterns:**
- All DB operations are async (SQLAlchemy 2.0 + asyncpg)
- Errors follow RFC 7807 (structured HTTP problem responses)
- Background jobs use ARQ (Redis-based queue)
- AI integration via Anthropic SDK

### Frontend (`healthcabinet/frontend/src/`)

- **`routes/`** — SvelteKit file-based routing with distinct layouts: `(app)/` (authenticated), `(auth)/`, `(admin)/`, `(marketing)/`.
- **`lib/api/`** — API client with auth headers, automatic token refresh (singleton promise pattern prevents concurrent refresh races), RFC 7807 error parsing.
- **`lib/stores/`** — Auth state using Svelte 5 runes (`$state`). Tokens are never stored in localStorage.
- **`lib/components/`** — shadcn-svelte UI components.

**Key patterns:**
- Svelte 5 runes syntax (`$state`, `$derived`, `$effect`) — not Svelte 4 stores
- `+page.server.ts` files handle form actions and server-side data loading
- TanStack Query (Svelte Query) for data fetching/caching

### Infrastructure

- **Docker Compose**: postgres 16, redis 7, backend, frontend services
- **Kubernetes**: Kustomize with overlays; backend has HPA configured
- **FluxCD**: GitOps deployment from this repo
- **SOPS**: Secrets management for K8s
- **CI/CD**: `.github/workflows/` — frontend-ci, backend-ci, deploy pipelines
