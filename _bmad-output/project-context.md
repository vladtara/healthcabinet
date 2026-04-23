---
project_name: 'HealthCabinet'
user_name: 'DUDE'
date: '2026-03-21'
sections_completed: ['technology_stack', 'backend_rules', 'frontend_rules', 'testing_rules', 'security_rules']
existing_patterns_found: 25
---

# Project Context for AI Agents

_Critical rules and patterns for HealthCabinet. Focus on unobvious details agents commonly miss._

_find and read CLAUDE.md_

---

## Technology Stack & Versions

**Frontend:**

- SvelteKit ^2.53.4, Svelte ^5.0.0, TypeScript ^5.0.0
- Vite ^6.0.0, Tailwind CSS ^4.0.0 (vite plugin, NOT PostCSS)
- 98.css (Windows 98 UI chrome, ~10KB), DM Sans (Google Fonts CDN)
- @tanstack/svelte-query 6.1.0
- Desktop-only MVP (1024px+). Mobile/tablet deferred to post-MVP.
- Vitest ^2.1.8 (unit), Playwright ^1.49.0 (E2E)
- ESLint 9 flat config, Prettier (useTabs: true, singleQuote: true, printWidth: 100)

**Backend:**

- Python 3.12+, FastAPI 0.135.1, SQLAlchemy 2.0 async, asyncpg, Alembic
- PyJWT 2.10.0 (NOT python-jose), passlib[bcrypt] 1.7.4, cryptography
- Anthropic SDK 0.84.0, ARQ + Redis, Stripe
- Ruff (line-length=100, target py312), MyPy strict, pytest-asyncio auto mode

---

## Critical Backend Rules

### SQLAlchemy 2.0 Style (MANDATORY)

- Always use `Mapped[T]` type hints and `mapped_column()` — NEVER old `Column()` style
- UUID primary keys: `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- Timestamps: `server_default=func.now()` for created_at; `onupdate=func.now()` for updated_at
- **CRITICAL**: `onupdate=func.now()` does NOT auto-refresh in-memory objects — call `await session.refresh(obj)` after updates if you need the new `updated_at` value
- Sessions use `expire_on_commit=False` — manual refresh required after commits

### Async Database Pattern

- All DB operations MUST be async — use `await session.execute(select(...))`, `await session.scalar(...)`
- `get_db()` auto-commits on success, auto-rolls back on exception — do NOT manually commit in endpoints
- Use `async_sessionmaker` with `class_=AsyncSession`

### FastAPI Router Conventions

- Routers use `prefix="/noun-plural"` and `tags=["noun"]`
- Always type `response_model` and `status_code` on route decorators
- Use `Depends(get_db)` and `Depends(get_current_user)` for injection
- **CRITICAL**: User ID always comes from `Depends(get_current_user)`, NEVER from request body

### Error Handling (RFC 7807)

- All errors return `{ type, title, status, detail, instance }` shape
- Use `HTTPException` — the global handler converts it to RFC 7807 automatically
- Domain-specific exceptions (e.g. `DuplicateEmailError`) should be caught and re-raised as `HTTPException`
- Preserve `Retry-After` and `WWW-Authenticate` headers on 429/401 responses

### Pydantic v2 Schemas

- Use `BaseModel` with `EmailStr`, `Annotated[T, Field(...)]`
- Share validators via module-level functions, decorate with `@field_validator`, `@classmethod`
- `gdpr_consent: Literal[True]` — type-system enforcement, not runtime check
- Passwords: enforce 72-byte UTF-8 limit (bcrypt truncates silently beyond this)

### Password & Auth Security

- Use direct `bcrypt` hashing — NOT `passlib.hash.bcrypt` (passlib 1.7.4 incompatible with bcrypt>=4.0)
- JWT access tokens: 15-min expiry, `"type": "access"` claim
- JWT refresh tokens: 30-day expiry, `"type": "refresh"` claim, httpOnly cookie scoped to `/api/v1/auth/refresh`
- **ALWAYS** validate the `"type"` claim when consuming tokens — access tokens must not be accepted as refresh tokens
- Timing-attack resistant login: run `verify_password()` with a dummy hash even when user is not found
- Email normalized to lowercase on creation and lookup

### Rate Limiting

- Login: 10 attempts/60s per-email, 50 attempts/60s per-IP
- Refresh: 10 calls/60s per-IP
- Rate limiter fails OPEN on Redis unavailability (intentional — log warning only)
- Use Lua script for atomic INCR + EXPIRE (prevents TOCTOU race)

### Background Jobs

- Use ARQ (not Celery) with Redis as broker
- Job functions are async

---

## Critical Frontend Rules

### Svelte 5 Runes (MANDATORY — NOT Svelte 4)

- State: `$state<T>()` — NEVER `writable()` or `readable()` stores
- Derived: `$derived(expr)` — NEVER `$: derived = ...`
- Side effects: `$effect(() => { ... })` — NEVER `$: { ... }` reactive blocks
- Props: `const { foo, bar } = $props()` — NEVER `export let foo`
- Children render: `{@render children()}` — NEVER `<slot />`
- Class files: use `.svelte.ts` extension (not `.ts`) for files using runes

### API Client Patterns

- All API calls go through `apiFetch<T>()` from `$lib/api/client.svelte.ts`
- It handles: auth headers, automatic token refresh on 401 (single retry), RFC 7807 error parsing
- Token refresh uses singleton deduplication (`refreshPromise`) — do NOT implement your own refresh logic
- Errors follow `ApiError` interface: `{ type, title, status, detail?, instance? }`

### Auth & Token Security

- Access tokens are NEVER stored in localStorage — memory-only via `tokenState`
- Refresh tokens are httpOnly cookies — JavaScript cannot read them
- Inactivity auto-logout fires after 30 minutes of no user interaction
- Check `authStore.isAuthenticated` for route guards, not token presence directly

### Routing & Layouts

- `(app)/` layout = authenticated routes (redirects to login if not authenticated)
- `(auth)/` layout = login/register pages
- `(admin)/` layout = admin-only routes
- `(marketing)/` layout = public pages
- Use `+page.server.ts` for form actions and server-side data loading
- Use TanStack Query (`createQuery`, `createMutation`) for client-side data fetching

### Styling

- Two-layer design system: 98.css provides Windows 98 UI chrome (buttons, inputs, panels, title bars, dialogs, progress bars); Tailwind CSS v4 handles layout, spacing, and custom health-domain styling
- Tailwind CSS v4 — uses Vite plugin (`@tailwindcss/vite`), NOT PostCSS config
- Font: DM Sans from Google Fonts CDN (overrides 98.css system font)
- Indentation: tabs (Prettier enforces `useTabs: true`)
- Desktop-only MVP (1024px+) — no mobile/tablet breakpoints in current scope

---

## Testing Rules

### Test Execution (MANDATORY)

- **ALL tests MUST run inside Docker Compose with build image — NEVER locally. No exceptions.**
- Always buld new images for frontend and backend
- For integration test alik conect ot db ,redis ,minio, aqm worker use always docker compose and test toghether
- Backend: `docker compose exec backend-test python run pytest` (add path/filter args as needed)
- Frontend: `docker compose exec frontend npm run test:unit`
- Can use bare `uv run pytest`, `npm run test`,  for unit test and linting
- Tests are only valid if they pass inside the Docker Compose environment (postgres, redis, MinIO are required dependencies)

### Backend Test Patterns

- `asyncio_mode = "auto"` — all async test functions are auto-detected, no `@pytest.mark.asyncio` needed
- Database fixture scope: `scope="session"` for engine creation (create/drop once), function scope for sessions (rollback after each test)
- **CRITICAL**: Use `await session.rollback()` in fixture teardown, NOT `drop_all` between tests
- Override `get_db` via `app.dependency_overrides[get_db] = override_get_db` — always clear in teardown
- Use `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` — NOT `TestClient`
- Test files: `tests/{domain}/test_{router|service|model}.py`
- Factory fixtures (`make_user`) return callables for flexible parameterization

### Integration Test Assertions

- Assert HTTP status code first, then response body
- Verify database state directly via `async_db_session.execute(select(...))` for write operations
- For auth endpoints: verify cookie attributes (httponly, secure, samesite=strict) via `response.headers`

### Frontend Test Patterns

- Unit tests: Vitest with jsdom environment, setup file at `src/lib/test-utils/setup.ts`
- E2E: Playwright against built preview (port 4173)
- Test files match `(.+\.)?(test|spec)\.[jt]s` pattern

---

## AWS & Data Residency

- **ALL** AWS resources MUST use `eu-central-1` region — no exceptions
- S3: MinIO-compatible (S3 API) for local dev; AWS S3 in production (same region)
- Never hardcode region strings — always use `settings.AWS_REGION`

---

## Code Organization

### Backend Module Structure

Each domain module (`auth/`, `documents/`, etc.) contains:

- `models.py` — SQLAlchemy ORM models
- `schemas.py` — Pydantic request/response models
- `router.py` — FastAPI route handlers (thin, delegates to service)
- `service.py` — business logic
- `dependencies.py` — FastAPI `Depends()` helpers

### New Domain Modules

When adding a new domain module, register its router in `app/main.py`:

```python
app.include_router(new_domain.router, prefix="/api/v1")
```

### Environment Configuration

- All settings in `app/core/config.py` via Pydantic `BaseSettings`
- Sensitive values: `SECRET_KEY`, `ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`
- Never access `os.environ` directly — always use `settings.*`
