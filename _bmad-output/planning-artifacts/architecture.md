---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2026-03-06'
lastStep: 8
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/product-brief-set-bmad-2026-03-06.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
workflowType: 'architecture'
project_name: 'set-bmad'
user_name: 'DUDE'
date: '2026-03-06'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
38 FRs across 7 categories. Core capabilities: universal document upload and multi-modal parsing (photo + PDF, any lab format/language), automated value extraction with confidence scoring, personalized health dashboard with trend visualization, AI interpretation with persistent cross-session memory, GDPR consent/export/deletion flows, and an admin operations panel with correction audit logging. Subscription billing is explicitly deferred from MVP implementation.

**Non-Functional Requirements:**
- Performance: <3s initial load, <2s dashboard render, <60s upload-to-insight, UI non-blocking during async processing
- Security: AES-256 at rest, TLS 1.2+ in transit, EU-region data residency from launch, admin elevated credentials, no third-party data sharing without DPAs
- Reliability: atomic value writes, retryable uploads (no data loss), 99% uptime, no silent extraction failures
- Scalability: 10x user growth without redesign, concurrent upload handling, indefinite per-user storage growth
- Compliance: GDPR Article 9 (special category health data), consent before collection, 30-day deletion SLA, portable export, processing records for audit
- Accessibility: WCAG AA minimum, semantic HTML, keyboard navigation, color not sole indicator

**Scale & Complexity:**

- Primary domain: Full-stack web application with AI/document intelligence pipeline
- Complexity level: High
- Estimated architectural components: ~7 active MVP domains (Auth, User Profile, Document Pipeline, Health Data Store, Dashboard/Visualization, AI Interpretation Engine, Admin Panel), with billing reserved for a later phase

### Technical Constraints & Dependencies

- SvelteKit SPA (CSR for authenticated app; SSR for marketing post-MVP)
- EU-region cloud infrastructure required from day one
- Managed services preferred for auth and storage (solo founder constraint)
- All AI provider integrations require signed Data Processing Agreements
- Health data never leaves EU-region infrastructure
- File upload: image/* and application/pdf; max size 20MB

### Cross-Cutting Concerns Identified

1. **GDPR compliance** — consent logging, deletion flows, export flows, DPAs for all third-party services; penetrates every data-touching component
2. **AI safety enforcement** — informational framing, uncertainty surfacing, no diagnostic output; applies to every AI response surface
3. **Encryption** — AES-256 at rest for all health documents and extracted values; TLS 1.2+ in transit
4. **Audit logging** — consent events (user ID, timestamp, policy version), admin value corrections (admin ID, original, new, reason), and session events
5. **Async document processing pipeline** — multi-modal AI parsing is latency-heavy (~10–60s); must be non-blocking with real-time status feedback (SSE/WebSockets)
6. **AuthN/AuthZ** — user vs admin role separation; session expiry on inactivity
7. **Error observability** — parsing failures, AI failures, low-confidence values all require surfacing paths to user and admin queue

---

## Starter Template Evaluation

### Primary Technology Domain

Decoupled full-stack web application: TypeScript SvelteKit frontend + Python FastAPI backend, deployed as separate services on Kubernetes. This split is driven by the Python-native AI/document processing pipeline and the requirement for a polished, reactive frontend.

### Architecture Overview

| Layer        | Technology                           | Rationale                                                                                             |
|--------------|--------------------------------------|-------------------------------------------------------------------------------------------------------|
| Frontend     | SvelteKit 2.53.4 + TypeScript        | SSR-capable (marketing post-MVP), excellent SPA mode, fast Vite toolchain, smaller bundle than React  |
| Backend API  | FastAPI 0.135.1 + Python 3.12+       | Async-first, native AI/ML library ecosystem, Pydantic v2 validation, automatic OpenAPI docs           |
| AI Pipeline  | LangGraph 1.x + LangChain-Core 1.x   | Current repo uses a LangGraph StateGraph for document processing and LangChain-based adapter seams in `app/ai/` |
| AI Observability | LangSmith                        | Trace every LangGraph node per document; debug extraction failures without log diving                 |
| Embeddings   | pgvector / embedding enrichment deferred | `reference_embeddings` and `interpretation_embeddings` are reserved for a later AI-hardening pass, not the current repo baseline |
| Background   | ARQ worker + Redis                   | Redis brokers ARQ jobs and SSE pub/sub; LangGraph executes inside the worker; graph checkpoint resume is deferred |
| Database     | PostgreSQL 16 + pgvector extension   | ACID guarantees + native vector search; CloudNative-PG operator on k8s (vendor-agnostic)             |
| ORM          | SQLAlchemy 2.0 (async) + Alembic     | Production-grade async ORM, type-safe queries, migration management                                   |
| File Storage | MinIO (S3-compatible)                | Runs on any k8s cluster; presigned URL API identical to S3 — zero backend code change; EU-local       |
| Auth         | Custom JWT (FastAPI + PyJWT)         | Simple MVP auth; access + refresh tokens; admin role separation via claims                            |
| Real-time    | Server-Sent Events (SSE via FastAPI) | Upload processing status stream; simpler than WebSockets for one-way server→client events            |
| AI           | Anthropic Claude API (multi-modal)   | Document image parsing + text interpretation; EU-compatible DPA available                            |

### Frontend Initialization

```bash
npx sv create healthcabinet-web
# Template: SvelteKit minimal
# TypeScript: Yes (strict)
# Add-ons: prettier, eslint, vitest, playwright, tailwindcss
```

**Architectural decisions provided by SvelteKit starter:**
- **Routing**: File-based (`src/routes/`) with `+page.svelte`, `+layout.svelte`, `+server.ts`
- **TypeScript**: strict mode via `tsconfig.json`
- **Styling**: Tailwind CSS v4 (Bloomberg/Stripe aesthetic aligned)
- **Testing**: Vitest (unit) + Playwright (e2e)
- **Build**: Vite 6, HMR, tree-shaking
- **State management**: Svelte 5 runes (`$state`, `$derived`) — no Redux/Zustand needed
- **SSR**: Enabled by default; authenticated app routes set to `export const ssr = false`

### Backend Initialization

```bash
uv init healthcabinet-api
cd healthcabinet-api
uv add "fastapi[standard]>=0.135.1" \
  "sqlalchemy[asyncio]>=2.0" asyncpg alembic \
  "pydantic-settings>=2.0" \
  "PyJWT>=2.10.0" "passlib[bcrypt]" \
  anthropic \
  python-multipart pillow pdf2image \
  "langchain-core>=1.0" "langgraph>=1.1" \
  "langchain-anthropic>=1.0" langsmith \
  "pgvector>=0.3" \
  arq redis \
  structlog sentry-sdk
uv add --dev pytest pytest-asyncio httpx
```

**Backend module structure (domain-based):**
```
healthcabinet-api/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── encryption.py
│   │   └── middleware.py
│   ├── auth/
│   ├── users/
│   ├── documents/
│   ├── processing/
│   ├── health_data/
│   ├── ai/
│   ├── billing/
│   └── admin/
├── alembic/
├── tests/
├── pyproject.toml
└── Dockerfile
```

**Note:** Project initialization should be the first implementation epic/story.

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- EAV health data schema — foundational DB design affects all health data queries
- Application-level encryption — affects every data write path from day one
- JWT auth strategy — gates all authenticated routes
- AWS region selection — determines all infrastructure setup

**Important Decisions (Shape Architecture):**
- ARQ + Redis for async processing pipeline
- SSE for real-time upload status
- Svelte Query for frontend data fetching
- 98.css + Tailwind CSS v4 for UI chrome and layout; unovis for charts
- SOPS + FluxCD for GitOps secrets management

**Deferred Decisions (Post-MVP):**
- Field-level encryption for AI conversation history
- Dashboard caching with Redis
- BFF/proxy layer for frontend
- WCAG full audit (before EU market launch)

---

### Data Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Health data schema | EAV hybrid | `health_values(document_id, name, value, unit, confidence)` rows |
| DB migrations | Alembic | SQLAlchemy-native, version-controlled |
| Caching | None (MVP) | Deferred |
| Max upload size | 20MB | Enforced at nginx ingress + FastAPI |
| Atomic writes | SQLAlchemy transactions | All-or-nothing per document |
| Vector search | pgvector extension | Extends existing PostgreSQL — no separate vector DB service |

**Health Values Schema:**
```sql
health_values (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id),
  document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  biomarker_name TEXT NOT NULL,
  canonical_biomarker_name TEXT NOT NULL,
  value_encrypted BYTEA NOT NULL,        -- decrypted only at repository layer
  unit           TEXT,
  reference_range_low  NUMERIC,
  reference_range_high NUMERIC,
  measured_at    TIMESTAMPTZ,
  confidence     NUMERIC NOT NULL,       -- 0.0–1.0
  needs_review   BOOLEAN NOT NULL DEFAULT FALSE,
  is_flagged     BOOLEAN DEFAULT FALSE,
  flagged_at     TIMESTAMPTZ,
  flag_reviewed_at TIMESTAMPTZ,
  flag_reviewed_by_admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
  extracted_at   TIMESTAMPTZ NOT NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW()
)
```

**Deferred Embedding Schemas (pgvector — future-state, not current repo baseline):**
```sql
-- Biomarker reference knowledge (normal ranges, clinical context) — admin-seeded
reference_embeddings (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,              -- e.g. "cholesterol_total"
  content     TEXT NOT NULL,             -- human-readable reference text
  embedding   vector(1024) NOT NULL,     -- voyage-3 output dimension
  source      TEXT,                      -- provenance label
  created_at  TIMESTAMPTZ DEFAULT NOW()
)

-- Per-user interpretation history — enables cross-session RAG
interpretation_embeddings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  content         TEXT NOT NULL,         -- interpretation text chunk
  embedding       vector(1024) NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW()
)

-- Indexes
CREATE INDEX ON reference_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON interpretation_embeddings USING ivfflat (embedding vector_cosine_ops);
```
> **Future-state note:** these tables are reserved for later AI-hardening work; they are not part of the current MVP repo baseline.

---

### Authentication & Security

| Decision | Choice | Rationale |
|---|---|---|
| Auth approach | Custom JWT (MVP) | No external dependency |
| Access token | 15 min, JS memory | Never in localStorage |
| Refresh token | 30 days, `httpOnly` + `Secure` + `SameSite=Strict` | CSRF-resistant |
| Password hashing | bcrypt (passlib) | Industry standard |
| Admin separation | `role` claim in JWT; `/api/v1/admin/` prefix | Separate elevated credentials |
| Session expiry | 30-min inactivity; refresh rotated on use | — |
| Encryption at rest | **Application-level AES-256-GCM** | Repository layer only; key via age (SOPS-encrypted in git) |
| Encryption in transit | TLS 1.2+ at nginx-ingress | HTTPS-only |
| CORS | Frontend origin only; no wildcard | Production exact match |

**Encryption key flow:**
```
age key (generated locally) → SOPS-encrypted in git
→ FluxCD decrypts at apply → FastAPI loads via Pydantic BaseSettings
→ repository.py encrypts before write, decrypts after read
```

---

### API & Communication Patterns

| Decision | Choice | Rationale |
|---|---|---|
| API style | REST `/api/v1/` | FastAPI-native, OpenAPI auto-docs |
| Frontend communication | Direct SvelteKit → FastAPI (CORS) | No BFF for MVP |
| Real-time status | SSE | One-way pipeline events |
| Rate limiting | Free: 5 uploads/day via `Depends(rate_limit_upload)` | Prevents AI cost runaway |
| Error responses | RFC 7807 | Consistent shape |
| API docs | Disabled in production | Dev tool only |

---

### AI Pipeline Architecture

| Decision | Choice | Rationale |
|---|---|---|
| Orchestration | LangGraph 1.x (StateGraph) | Current implemented graph is `load_document → extract_values → persist_values → generate_interpretation? → finalize_document` |
| Embedding model | Voyage-3 (Anthropic) | Medical-tuned; 1024-dim output; EU DPA available; same vendor as Claude |
| Vector store | pgvector on existing PostgreSQL | Zero new service; ivfflat index sufficient for MVP corpus size |
| RAG — reference knowledge | Deferred from current repo baseline | `reference_embeddings` lookup and enrichment nodes are not implemented in the live codebase yet |
| RAG — cross-session memory | Deferred from current repo baseline | `interpretation_embeddings` retrieval is planned, but current AI features do not depend on it |
| Agent pattern | Deterministic graph with explicit node boundaries | Retryable orchestration and conditional interpretation remain; reference-enrichment expansion is deferred |
| State persistence | ARQ + Redis | Redis backs the worker queue and SSE pub/sub; LangGraph checkpoint persistence is deferred |
| Observability | LangSmith | Traces every node per `document_id`; visible in LangSmith dashboard |
| Worker deployment | Separate k8s Deployment | Independent scaling from API; same codebase, different entrypoint |
| Safety enforcement | `safety.py` applied at `generate_interpretation` node | `inject_disclaimer()`, `validate_no_diagnostic()`, `surface_uncertainty()` — unchanged |

**Current-state note:**
- Document processing is already orchestrated through LangGraph with explicit node boundaries and safe fallback behavior
- Reference-enrichment nodes, vector-memory retrieval, and Redis-backed checkpoint resume remain planned follow-on capabilities, not current implementation facts
- Past interpretation retrieval is called conditionally at `generate_interpretation` node only when `user_id` has prior documents

---

### Frontend Architecture

| Decision | Choice | Version |
|---|---|---|
| State management | Svelte 5 runes | Svelte 5 |
| Server-state | `@tanstack/svelte-query` | 6.1.0 |
| Component library | `98.css` + custom Svelte 5 components | ~10KB |
| Charts | `@unovis/svelte` | 1.6.2 |
| Forms | SvelteKit form actions + Zod | — |

---

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|---|---|---|
| Cloud | Any k8s cluster (EU region) | Vendor-agnostic; local: k3d; prod: Hetzner/OVH/Scaleway/any |
| Kubernetes | k3d (local) / any k8s (prod) | k3d is most production-like for local dev |
| CI/CD | GitHub Actions | Unchanged |
| GitOps | FluxCD | Unchanged |
| Secrets | k8s Secrets + SOPS (age key) | age key replaces KMS — no cloud provider dependency |
| Container registry | GHCR (GitHub Container Registry) | Free, GitHub Actions integrated, no vendor lock-in |
| Database | CloudNative-PG operator on k8s | PostgreSQL 16 + pgvector; HA-capable; runs on any k8s cluster |
| Object storage | MinIO on k8s | S3-compatible API; presigned URLs work identically; EU-local |
| Monitoring | Prometheus + Grafana (kube-prometheus-stack) | Unchanged |
| Error tracking | Sentry | Unchanged |
| Ingress | ingress-nginx | Universal; works on any k8s cluster (replaces ALB Ingress Controller) |
| Environments | dev / staging / prod (Kustomize overlays) | Unchanged |

**Deployment pipeline:**
```
GitHub push → Actions: lint + test + build → push GHCR (git SHA tag)
→ update FluxCD image tag → FluxCD applies to k8s cluster → Prometheus scrapes
```

**Encryption key flow (no KMS):**
```
age key (generated locally, stored in git as SOPS-encrypted secret)
→ FluxCD decrypts at apply → FastAPI loads via Pydantic BaseSettings
→ repository.py encrypts before write, decrypts after read
```

---

### Decision Impact Analysis

**Implementation Sequence:**
1. Monorepo structure (`frontend/` + `backend/` + `k8s/`)
2. k8s cluster bootstrap: k3d local; ingress-nginx; FluxCD + SOPS age key; GHCR registry
3. Infrastructure on k8s: CloudNative-PG (PostgreSQL 16 + pgvector), MinIO, Redis
4. GitHub Actions pipelines (build → push GHCR → FluxCD image update)
5. FastAPI skeleton (core: config, DB, security, encryption, middleware)
6. Alembic initial schema (users, documents, health_values, consent_logs, audit_logs, ai_memories + pgvector extension reserved for later AI-hardening work)
7. SvelteKit skeleton (routing, auth flows, 98.css + Tailwind)
8. Auth (register, login, refresh, JWT middleware)
9. Document upload → MinIO presigned URL → ARQ worker enqueue
10. LangGraph graph (`load_document → extract_values → persist_values → generate_interpretation? → finalize_document`)
11. Reference-embedding enrichment remains deferred until after the current MVP admin/GDPR path
12. Health dashboard (Svelte Query + unovis charts)
13. AI interpretation + safety wrapper + LangSmith tracing
14. Billing integration deferred to Phase 2
15. Admin panel
16. GDPR flows (delete, export, consent logging)

**Cross-Component Dependencies:**
- Encryption key before any health data write
- ARQ + Redis before processing pipeline tests
- Billing/webhook integration remains out of MVP scope until a later phase
- SOPS + FluxCD bootstrapped before any k8s secrets in git

---

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 7 areas — naming conventions, API response shape, date formats, error structures, file organization, test placement, SSE event naming.

---

### Naming Patterns

**Database:** `snake_case` plural tables (`users`, `health_values`), UUID PKs, `{table_singular}_id` FKs, `idx_{table}_{cols}` indexes

**API:** `snake_case` plural endpoints (`/api/v1/health_values`), `snake_case` JSON fields throughout — no transformation layer

**Python:** `snake_case` functions/files, `PascalCase` classes, `PascalCase + Schema` suffix for Pydantic models, `SCREAMING_SNAKE_CASE` constants

**TypeScript/Svelte:** `camelCase` variables/functions, `PascalCase.svelte` components, TypeScript interfaces mirror API `snake_case` exactly

> **Boundary rule:** API returns `snake_case`. Frontend uses `snake_case` directly. No transformation.

---

### Structure Patterns

**Backend per-domain:**
```
app/{domain}/
├── router.py       # routes only
├── service.py      # business logic, no DB
├── repository.py   # DB + encryption/decryption
├── schemas.py      # Pydantic models
├── models.py       # SQLAlchemy ORM
└── dependencies.py # FastAPI Depends()
```

**Frontend:**
```
src/
├── routes/(app)/    # ssr=false, auth guard
├── routes/(auth)/   # public
├── routes/(admin)/  # admin role guard
├── routes/(marketing)/ # SSR, post-MVP
└── lib/
    ├── api/         # fetch wrappers
    ├── components/ui/    # 98.css primitives
    ├── components/health/ # domain components
    ├── stores/      # $state runes
    ├── types/       # API interface mirrors
    └── test-utils/  # shared mock factories, render wrappers
```

**Test placement:**
- Backend: `tests/` mirroring `app/`; shared `tests/conftest.py` with async DB session + factories
- Frontend: co-located `*.test.ts` unit; top-level `tests/e2e/` Playwright; `src/lib/test-utils/` shared helpers

---

### Format Patterns

**API responses:** Direct body for single resource; `{items, total, page, page_size}` for lists; RFC 7807 for errors

**Data formats:** ISO 8601 UTC everywhere, `true`/`false` booleans, lowercase UUID strings, `null` explicit, monetary in cents

---

### Communication Patterns

**SSE events** (`document.{action}`):
```
document.upload_started → document.reading → document.extracting
→ document.generating → document.completed | document.failed | document.partial
```
Payload: `{event, document_id, progress, message}`

**SSE testing:** `httpx.AsyncClient(stream=True)` — assert full event **sequence**, not terminal state

**LangGraph jobs:** graph function names `snake_case`; Redis queue naming and routing must reflect MVP processing needs only. Paid-tier queueing is deferred with billing.

---

### Process Patterns

**Errors:** RFC 7807 from FastAPI; domain exceptions in `{domain}/exceptions.py`; never leak stack traces; global handler → Sentry + structlog. Frontend: display `error.detail` only; never raw objects.

**Loading:** `is{Action}` naming; Svelte Query `isPending`; never blank — always skeleton/spinner

**Validation:** Pydantic = source of truth; Zod on frontend; confidence `< 0.7` always surfaced

---

### Enforcement Guidelines

**All AI Agents MUST:**
- `snake_case` DB/API/Python; `PascalCase.svelte` components
- DB queries in `repository.py` only; business logic in `service.py` only; routes in `router.py` only
- **Encryption/decryption in `repository.py` only** — never service or router
- ISO 8601 UTC for all datetimes — never format in API layer
- RFC 7807 error shape always
- **`user_id` via `Depends(get_current_user)` only** — never from body/params
- **Rate limiting via `Depends(rate_limit_upload)`** — never inline
- **AI endpoints use the authenticated user path only in MVP** — no paid-tier gate until billing is reintroduced

**Enforcement:** Ruff + mypy (backend), ESLint + Prettier (frontend), pre-commit hooks, PR checklist

**Anti-patterns (never do):** DB call in router · encryption in service · user_id from body · inline rate limiting · camelCase in TypeScript API interfaces

---

## Project Structure & Boundaries

### FR Categories → Structural Mapping

| FR Category | Backend | Frontend Route |
|---|---|---|
| User Account (FR1–FR6) | `app/auth/` + `app/users/` | `(auth)/login`, `(auth)/register`, `(app)/settings/` |
| Document Management (FR7–FR13) | `app/documents/` | `(app)/documents/`, `(app)/documents/upload/` |
| Health Dashboard (FR14–FR17) | `app/health_data/` | `(app)/dashboard/` |
| AI Interpretation (FR18–FR22) | `app/ai/` | `(app)/documents/[document_id]/` |
| Processing Feedback (FR23–FR25) | `app/processing/` (SSE) | `health/ProcessingStatusBanner.svelte` |
| Subscription & Billing (FR26–FR29, Phase 2) | Reserved for later phase | Reserved for later phase |
| GDPR Compliance (FR30–FR33) | `app/users/` (GDPR flows) | `(app)/settings/` |
| Admin & Operations (FR34–FR38) | `app/admin/` | `(admin)/admin/` |

---

### Complete Project Directory Structure

**Monorepo Root:**
```
healthcabinet/
├── README.md
├── .gitignore
└── .github/
    └── workflows/
        ├── backend-ci.yml
        ├── frontend-ci.yml
        └── deploy.yml
```

**Frontend (`frontend/`):**
```
frontend/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── .eslintrc.cjs
├── .prettierrc
├── Dockerfile
├── .env.example
├── static/favicon.png
├── tests/e2e/
│   ├── auth.test.ts
│   ├── upload.test.ts
│   └── dashboard.test.ts
└── src/
    ├── app.html
    ├── app.css
    ├── hooks.server.ts
    ├── lib/
    │   ├── api/
    │   │   ├── client.ts            # Base fetch: auth headers, RFC 7807 error parsing
    │   │   ├── auth.ts
    │   │   ├── documents.ts
    │   │   ├── health-data.ts
    │   │   ├── ai.ts
    │   │   └── billing.ts
    │   ├── components/
    │   │   ├── ui/                  # 98.css primitives
    │   │   │   ├── Button.svelte
    │   │   │   ├── Card.svelte
    │   │   │   ├── Dialog.svelte
    │   │   │   ├── Input.svelte
    │   │   │   ├── Badge.svelte
    │   │   │   ├── Skeleton.svelte
    │   │   │   └── Tabs.svelte
    │   │   └── health/
    │   │       ├── BiomarkerTrendChart.svelte      # FR15
    │   │       ├── HealthValueBadge.svelte          # FR14
    │   │       ├── DocumentUploadZone.svelte        # FR7
    │   │       ├── ProcessingStatusBanner.svelte    # FR23
    │   │       ├── AiInterpretationCard.svelte      # FR18
    │   │       ├── ReasoningTrail.svelte            # FR20
    │   │       ├── ConfidenceWarning.svelte         # FR9
    │   │       ├── OnboardingProfileForm.svelte     # FR3
    │   │       └── TestRecommendations.svelte       # FR16
    │   ├── stores/
    │   │   ├── auth.svelte.ts
    │   │   └── upload.svelte.ts
    │   ├── types/
    │   │   ├── api.ts
    │   │   ├── auth.ts
    │   │   ├── document.ts
    │   │   ├── health-value.ts
    │   │   └── billing.ts
    │   └── test-utils/
    │       ├── render.ts
    │       └── factories.ts
    └── routes/
        ├── (auth)/
        │   ├── +layout.svelte
        │   ├── login/
        │   │   ├── +page.svelte
        │   │   └── +page.server.ts
        │   └── register/
        │       ├── +page.svelte
        │       └── +page.server.ts
        ├── (app)/
        │   ├── +layout.svelte            # ssr=false, auth guard
        │   ├── +layout.server.ts
        │   ├── onboarding/
        │   │   ├── +page.svelte
        │   │   └── +page.server.ts
        │   ├── dashboard/
        │   │   ├── +page.svelte          # FR14–17
        │   │   └── +page.ts
        │   ├── documents/
        │   │   ├── +page.svelte          # FR11
        │   │   ├── +page.ts
        │   │   ├── upload/
        │   │   │   └── +page.svelte      # FR7, FR23–25
        │   │   └── [document_id]/
        │   │       ├── +page.svelte      # FR18–22
        │   │       └── +page.ts
        │   └── settings/
        │       ├── +page.svelte          # FR3–6, FR26–33
        │       └── +page.server.ts
        ├── (admin)/
        │   ├── +layout.svelte            # admin role guard
        │   └── admin/
        │       ├── +page.svelte          # FR34
        │       ├── documents/
        │       │   └── +page.svelte      # FR35–36, FR38
        │       └── users/
        │           └── +page.svelte      # FR37
        └── (marketing)/
            ├── +layout.svelte
            └── +page.svelte
```

**Backend (`backend/`):**
```
backend/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── conftest.py              # async_db_session, test_client, make_user(), make_document()
│   ├── auth/
│   │   ├── test_router.py
│   │   └── test_service.py
│   ├── documents/
│   │   ├── test_router.py
│   │   └── test_service.py
│   ├── processing/
│   │   ├── test_graph.py        # LangGraph orchestration regression tests
│   │   ├── test_worker.py       # thin-worker fallback and delegation tests
│   │   ├── test_router.py       # SSE/status route coverage
│   │   ├── test_events.py       # Redis-backed event publication tests
│   │   ├── test_extractor.py    # extraction-boundary coverage
│   │   └── test_normalizer.py   # normalization and confidence scoring
│   ├── health_data/
│   │   └── test_repository.py
│   ├── ai/
│   │   ├── test_safety.py
│   │   └── test_service.py
│   └── billing/
│       └── test_router.py
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── security.py
    │   ├── encryption.py        # AES-256-GCM encrypt_bytes/decrypt_bytes
    │   └── middleware.py
    ├── auth/
    │   ├── router.py            # POST /auth/register, /login, /refresh, /logout
    │   ├── service.py
    │   ├── repository.py
    │   ├── schemas.py
    │   ├── models.py            # User(id, email, hashed_password, role, tier)
    │   └── dependencies.py      # get_current_user, require_admin, future access guards if needed
    ├── users/
    │   ├── router.py            # GET/PUT /users/me, DELETE /users/me, GET /users/me/export
    │   ├── service.py           # GDPR cascade delete, data export ZIP builder
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models.py            # UserProfile, ConsentLog
    ├── documents/
    │   ├── router.py            # POST /documents/upload-url, /notify, GET list, GET/DELETE {id}
    │   ├── service.py
    │   ├── repository.py        # encrypt s3_key before write
    │   ├── schemas.py
    │   ├── models.py            # Document(id, user_id, s3_key_encrypted, status)
    │   └── storage.py           # presigned upload/read URL generation
    ├── processing/
    │   ├── router.py            # GET /documents/{id}/status → SSE
    │   ├── worker.py            # ARQ entrypoint: invoke LangGraph per document
    │   ├── graph.py             # LangGraph StateGraph definition
    │   ├── nodes/
    │   │   ├── load_document.py         # fetch metadata + bytes for the graph run
    │   │   ├── extract_values.py        # extractor + normalizer boundary
    │   │   ├── persist_values.py        # atomic write to health_values + processing events
    │   │   ├── generate_interpretation.py  # AI interpretation boundary + safety
    │   │   └── finalize_document.py     # terminal status/event handling
    │   ├── normalizer.py        # unit normalization, confidence scoring
    │   ├── schemas.py           # ProcessingEvent SSE payload; LangGraph state + fallback types
    │   ├── events.py            # SSE publication helpers
    │   ├── tracing.py           # LangSmith tracing hooks
    │   └── dependencies.py      # rate_limit_upload(current_user, redis)
    ├── health_data/
    │   ├── router.py            # GET /health_values, /timeline, PUT /{id}/flag
    │   ├── service.py           # trend calc, baseline generation
    │   ├── repository.py        # EAV queries; decrypt value after read
    │   ├── schemas.py
    │   └── models.py            # HealthValue (EAV)
    ├── ai/
    │   ├── router.py            # GET /documents/{id}/interpretation, POST /ai/ask
    │   ├── service.py
    │   ├── repository.py        # AiMemory read/write; encrypt context before write
    │   ├── schemas.py
    │   ├── models.py            # AiMemory(user_id, context_json_encrypted)
    │   ├── claude_client.py     # Anthropic SDK wrapper, retry, token tracking
    │   └── safety.py            # inject_disclaimer(), validate_no_diagnostic(), surface_uncertainty()
    ├── billing/                 # Reserved for Phase 2 billing work; not part of MVP execution
    │   ├── router.py
    │   ├── service.py
    │   ├── repository.py
    │   ├── schemas.py
    │   └── models.py
    └── admin/
        ├── router.py            # GET /admin/metrics, /queue, /flags, /users; POST corrections and flag review; PATCH user status
        ├── service.py
        ├── repository.py
        └── schemas.py
```

**Infrastructure (`k8s/`):**
```
k8s/
├── clusters/production/
│   ├── flux-system/             # FluxCD bootstrap
│   └── apps/kustomization.yaml
├── apps/
│   ├── backend/
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml         # ingress-nginx: /api/* → backend:8000; SSE timeout ≥120s
│   │   ├── hpa.yaml             # min 2, max 10
│   │   └── secrets.enc.yaml     # SOPS age-encrypted
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml         # ingress-nginx: /* → frontend:3000
│   ├── worker/
│   │   ├── deployment.yaml      # separate image; CMD: python -m app.processing.worker
│   │   └── hpa.yaml             # scale independently from API
│   └── infrastructure/
│       ├── ingress-nginx/kustomization.yaml      # replaces ALB Ingress Controller
│       ├── cloudnative-pg/                       # replaces RDS
│       │   ├── cluster.yaml     # PostgreSQL 16 + pgvector extension
│       │   └── kustomization.yaml
│       ├── minio/               # replaces AWS S3
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── secrets.enc.yaml
│       ├── redis/deployment.yaml
│       └── monitoring/kustomization.yaml         # kube-prometheus-stack
└── overlays/
    ├── dev/kustomization.yaml
    ├── staging/kustomization.yaml
    └── prod/kustomization.yaml
```

---

### Architectural Boundaries

**Data Flow — Core Loop (Upload → Insight):**
```
User drops file
  → POST /documents/upload-url       (get MinIO presigned PUT — S3-compatible)
  → PUT MinIO presigned URL          (direct, 20MB limit enforced at ingress-nginx + FastAPI)
  → POST /documents/{id}/notify      (trigger processing)
  → ARQ worker invokes LangGraph run
  → GET /documents/{id}/status       (SSE stream opened)
  ← document.reading → extracting → generating → completed
      [LangGraph nodes: load_document → extract_values → persist_values
       → generate_interpretation? → finalize_document]
  → Svelte Query invalidate → dashboard re-fetches
```

**LangGraph Processing Graph (app/processing/graph.py):**
```
[load_document]          load document metadata + bytes
        ↓
[extract_values]          extractor + normalizer → normalized values
        ↓
[persist_values]         atomic SQLAlchemy transaction → health_values rows
        ↓
[generate_interpretation] conditional on persisted normalized values
                          safety wrapper (inject_disclaimer, validate_no_diagnostic,
                          surface_uncertainty) preserved from earlier epics
        ↓
[finalize_document]      document.completed | document.partial | document.failed

Current graph preserves existing fallback semantics:
- `completed` for successful persistence without review-needed outcomes
- `partial` when low-confidence values exist or later-stage failures occur after values already exist
- `failed` only for first-time no-value failure without recoverable persisted data

Redis is currently used for ARQ and SSE publication. Redis-backed graph checkpoint resume remains deferred.
LangSmith traces full graph execution per document_id.
```

**Encryption Boundary:** Repository layer only — `documents/repository.py`, `health_data/repository.py`, `ai/repository.py`

**AI Access in MVP:** authenticated users can access interpretation, follow-up Q&A, and pattern-detection features without paid gating. Billing-triggered access control is deferred from this architecture baseline.

**GDPR Boundary:** Epic 6 target behavior is for `DELETE /users/me` to delete user-owned documents, health values, AI memories, and profile data; retain `consent_logs` via an explicit schema/workflow adjustment away from the current user-delete cascade; and preserve the operator audit envelope by redacting user-linked `audit_logs` payloads and foreign keys during erasure. `GET /users/me/export` should stream ZIP exports of the user's decrypted personal data, including account metadata and admin-correction history relevant to that user.

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are compatible and version-verified. SvelteKit 2.53.4 + Svelte 5 runes is fully supported by `@tanstack/svelte-query` v6.1.0 (runes-native) and `98.css` (~10KB, framework-agnostic CSS). FastAPI 0.135.1 is compatible with SQLAlchemy 2.0 async, Pydantic v2, and PyJWT. ARQ uses Redis natively — the same Redis instance also serves rate limiting counters and SSE publication. DM Sans loaded via Google Fonts CDN. No version conflicts detected.

**Pattern Consistency:**
All patterns align with the stack. `snake_case` throughout Python/API is FastAPI/Pydantic's default — zero friction. Svelte 5 runes replace traditional stores — patterns updated accordingly. Repository/service/router separation is a natural fit for FastAPI's dependency injection model. SSE is a first-class FastAPI primitive — no external library needed.

**Structure Alignment:**
Project structure directly reflects domain modules defined in decisions. Each backend domain module maps 1:1 to an FR category. Each frontend route group maps to a user-facing feature. Integration points (SSE timeout, SOPS secrets, ALB routing) are all explicitly defined in k8s manifests.

---

### Requirements Coverage Validation ✅

**All 38 FRs covered:**

| FR Range | Coverage |
|---|---|
| FR1–FR6 (Auth + Account) | `app/auth/` + `app/users/`; JWT + GDPR flows |
| FR7–FR13 (Documents) | `app/documents/` + S3 presigned; EAV schema |
| FR14–FR17 (Dashboard) | `app/health_data/`; baseline from profile; trend calc |
| FR18–FR22 (AI) | `app/ai/`; safety wrapper; authenticated user access in MVP |
| FR23–FR25 (Processing feedback) | `app/processing/` SSE; partial extraction path |
| FR26–FR29 (Billing, Phase 2) | Deferred from MVP implementation |
| FR30–FR33 (GDPR) | consent_logs table; ZIP export; delete flow with audit-log redaction/retention policy |
| FR34–FR38 (Admin) | `app/admin/`; correction audit log; metrics |

**NFR Coverage:**

| NFR | Architectural Support |
|---|---|
| Performance <3s load | Vite tree-shaking; Svelte Query caching; CDN for static assets |
| Performance <60s processing | ARQ async pipeline; SSE non-blocking feedback |
| Security AES-256 | `core/encryption.py`; repository-layer enforcement |
| Security EU residency | All AWS resources pinned to eu-central-1 |
| Reliability atomic writes | SQLAlchemy transactions per document |
| Reliability no data loss | Retryable uploads; ARQ job retry on failure |
| Scalability 10x | EKS HPA (min 2, max 10); RDS Multi-AZ post-MVP; S3 unlimited |
| Compliance GDPR | consent_logs retained; audit logs redacted on erasure; export ZIP; DPAs required |
| Accessibility WCAG AA | 98.css high-contrast chrome; semantic HTML required by design; color + text labels |

---

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical and important decisions documented with verified versions. Deferred decisions explicitly listed with rationale. No ambiguous decisions remain.

**Structure Completeness:** Complete file tree for all three layers (frontend, backend, k8s). Every FR maps to a specific file or directory. Integration points (SSE timeout config, SOPS secrets path, ALB routing rules) explicitly specified.

**Pattern Completeness:** 7 conflict areas addressed. Anti-patterns with before/after code examples. Enforcement via linting tools + pre-commit + PR checklist. Party mode review added 6 additional precision rules.

---

### Gap Analysis Results

**Critical Gaps:** None identified.

**Important Gaps (post-MVP backlog):**
- AI memory context format schema not yet defined — specify structure of `context_json` before implementing `ai/repository.py`
- Reference ranges database not specified — biomarker normal ranges (age/sex-adjusted) need a data source (embedded JSON lookup vs. separate table)
- Email service not specified — needed for: password reset, upload completion notification (post-MVP). Suggest AWS SES (eu-central-1) when required.

**Nice-to-Have:**
- OpenAPI client code generation (e.g. `openapi-typescript`) to auto-generate TypeScript types from FastAPI schema — eliminates manual interface maintenance
- Database diagram for the 6 core tables

---

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (38 FRs, 6 NFR categories)
- [x] Scale and complexity assessed (High complexity, AI pipeline)
- [x] Technical constraints identified (EU residency, solo founder, GDPR)
- [x] Cross-cutting concerns mapped (7 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented with verified versions
- [x] Technology stack fully specified (SvelteKit 2.53.4, FastAPI 0.135.1, PG 16)
- [x] Integration patterns defined (SSE, ARQ, S3 presigned; billing integration deferred)
- [x] Performance, security, and compliance addressed

**✅ Implementation Patterns**
- [x] Naming conventions (DB, API, Python, TypeScript)
- [x] Structure patterns (router/service/repository separation)
- [x] Communication patterns (SSE events, ARQ jobs)
- [x] Process patterns (error handling, loading states, validation)
- [x] Enforcement (linting, pre-commit, PR checklist, anti-patterns)

**✅ Project Structure**
- [x] Complete directory structure (frontend + backend + k8s)
- [x] Component boundaries established
- [x] All 38 FRs mapped to specific files/directories
- [x] Integration points and data flows documented

---

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High**

**Key Strengths:**
- Application-level encryption decided and boundary-enforced before a single line is written — prevents a class of security mistakes entirely
- EAV health data schema handles the core product innovation (any lab, any format) without schema migrations for new biomarkers
- Decoupled frontend/backend enables Python AI ecosystem for the hardest technical problem (document parsing) while keeping frontend fast and lean
- GitOps (FluxCD + SOPS) is production-grade from day one — not bolted on later
- Party mode review surface 6 additional precision rules closing real implementation conflict risks

**Areas for Future Enhancement:**
- AI memory context schema (before implementing `ai/repository.py`)
- Reference ranges data source (before implementing `health_data/service.py` baseline generation)
- Email service selection (before post-MVP notification features)
- OpenAPI → TypeScript codegen (removes manual type maintenance overhead)
- Redis caching layer (when dashboard query latency becomes measurable)

---

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented — versions are pinned and verified
- Use implementation patterns consistently — anti-patterns section shows what NOT to do
- Respect router/service/repository boundaries — this is enforced by linting
- Encryption happens in `repository.py` only — any agent that calls `encrypt_bytes()` outside this layer has a bug
- `user_id` comes from `Depends(get_current_user)` only — no exceptions
- Refer to this document for all architectural questions before making any independent decision

**First Implementation Story:**
```bash
# Story 1: Monorepo scaffold + infrastructure baseline
# Frontend
npx sv create frontend --template minimal --types ts --no-install
# Backend
uv init backend && cd backend
uv add "fastapi[standard]>=0.135.1" "sqlalchemy[asyncio]>=2.0" asyncpg alembic \
  "pydantic-settings>=2.0" "PyJWT>=2.10.0" "passlib[bcrypt]" \
  stripe anthropic python-multipart pillow pdf2image arq redis structlog sentry-sdk
uv add --dev pytest pytest-asyncio httpx
# Infrastructure
mkdir -p k8s/apps/{backend,frontend,worker,infrastructure} k8s/overlays/{dev,staging,prod}
# FluxCD bootstrap (requires AWS EKS cluster + GitHub PAT)
flux bootstrap github --owner=<org> --repository=healthcabinet --path=k8s/clusters/production
```
