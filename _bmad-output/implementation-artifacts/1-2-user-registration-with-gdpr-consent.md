# Story 1.2: User Registration with GDPR Consent

Status: done

## Story

As a visitor,
I want to register for an account with my email and password after providing explicit consent to health data processing,
so that I can access HealthCabinet with my data handled lawfully and transparently.

## Acceptance Criteria

1. **Given** a visitor navigates to `/register` **When** they submit a valid email and password (min 8 chars) with GDPR consent checked **Then** a new user record is created in the `users` table with bcrypt-hashed password **And** a consent event is written to `consent_logs` **And** the user receives a JWT access token + refresh token **And** they are redirected to `/onboarding`

2. **Given** a visitor is on the registration page **When** the GDPR consent checkbox is not checked **Then** the submit button is disabled and the form cannot be submitted **And** the checkbox is never pre-checked by default

3. **Given** a visitor submits valid registration with consent checked **When** the registration completes **Then** a consent event is written to `consent_logs` with: `user_id`, `consented_at` (UTC ISO 8601), `consent_type = "health_data_processing"`, `privacy_policy_version` **And** no health data is stored prior to this consent event completing

4. **Given** a visitor submits a registration with an already-registered email **When** the API processes the request **Then** a 409 response is returned with RFC 7807 error shape **And** the frontend displays "An account with this email already exists" below the email field

5. **Given** a visitor submits a registration with an invalid email format **When** frontend validation runs on blur **Then** an inline error message appears below the email field with color + text (not color alone, per WCAG AA) **And** the form is not submitted to the API

6. **Given** the registration page is rendered **When** a keyboard-only user navigates the form **Then** all fields and the submit button are reachable via Tab key **And** the consent checkbox is operable via Space key **And** form submission is possible via Enter key

## Tasks / Subtasks

- [x] Task 1: Backend — Registration schemas (AC: #1, #3, #4)
  - [x] Add `RegisterRequest` Pydantic model to `backend/app/auth/schemas.py`: fields `email: EmailStr`, `password: str` (min 8 chars), `gdpr_consent: bool` (must be True), `privacy_policy_version: str`
  - [x] Add `RegisterResponse` Pydantic model: fields `id: UUID`, `email: str`, `access_token: str`, `token_type: str = "bearer"`
  - [x] Add `DuplicateEmailError` exception to `backend/app/auth/exceptions.py` (create file if not exists)

- [x] Task 2: Backend — Repository layer (AC: #1, #3)
  - [x] Implement `create_user(db, email, hashed_password) -> User` in `backend/app/auth/repository.py`
  - [x] Implement `get_user_by_email(db, email) -> User | None` in `backend/app/auth/repository.py`
  - [x] Implement `create_consent_log(db, user_id, consent_type, privacy_policy_version) -> ConsentLog` in `backend/app/auth/repository.py`
  - [x] Note: `consent_logs` model may be in `app/users/models.py` per architecture — check and import from there if so; do NOT duplicate

- [x] Task 3: Backend — Service layer (AC: #1, #3, #4)
  - [x] Implement `register_user(db, email, password, privacy_policy_version) -> (User, str)` in `backend/app/auth/service.py`
  - [x] Call `get_user_by_email` first; if found raise `DuplicateEmailError`
  - [x] Hash password via `hash_password()` from `app/core/security.py`
  - [x] Call `create_user`, then `create_consent_log` within same DB transaction
  - [x] Generate JWT access token via `create_access_token()` from `app/core/security.py`
  - [x] Return `(user, access_token)`

- [x] Task 4: Backend — Router (AC: #1, #4)
  - [x] Add `POST /auth/register` to `backend/app/auth/router.py`
  - [x] No auth dependency (public endpoint)
  - [x] Call service `register_user`; catch `DuplicateEmailError` → raise HTTP 409 with RFC 7807 body
  - [x] Return `RegisterResponse` with 201 status
  - [x] Set refresh token as `httpOnly; Secure; SameSite=Strict` cookie (30-day expiry) in response

- [x] Task 5: Backend — Wire refresh token cookie + update main.py router include (AC: #1)
  - [x] Confirm `app/auth/router.py` is included in `app/main.py` with prefix `/auth`
  - [x] Implement `create_refresh_token(user_id)` in `app/core/security.py` if not already present (30-day expiry, `sub=str(user_id)`)

- [x] Task 6: Frontend — API client update (AC: #1, #4)
  - [x] Add `register(email, password, gdpr_consent, privacy_policy_version)` function to `frontend/src/lib/api/auth.ts`
  - [x] Use existing `client.ts` fetch wrapper (handles RFC 7807 error parsing automatically)
  - [x] On success, call `setAccessToken(token)` on auth store

- [x] Task 7: Frontend — Register page implementation (AC: #1–#6)
  - [x] Implement `frontend/src/routes/(auth)/register/+page.svelte` with Svelte 5 runes (`$state`)
  - [x] Form fields: email (`<input type="email">`), password (`<input type="password">`), password confirmation (client-side match only), GDPR consent checkbox
  - [x] GDPR checkbox: never pre-checked; submit button `disabled` when `!consentChecked`
  - [x] Email blur handler: validate format inline, show error below field (text + color, not color alone)
  - [x] On submit: call `register()`, store access token in auth store, redirect to `/onboarding`
  - [x] Display 409 error "An account with this email already exists" below email field
  - [x] Use shadcn-svelte components: `Input`, `Button`, `Label`, `Checkbox` (from `$lib/components/ui/`)
  - [x] All labels explicitly associated with their inputs via `<label for="...">` or `<Label>`
  - [x] No `<script context="module">` needed; `ssr = false` is inherited from `(auth)` layout — verify or set in `+page.ts` if needed

- [x] Task 8: Frontend — Auth store update (AC: #1)
  - [x] Add `setAccessToken(token: string)` to `frontend/src/lib/stores/auth.svelte.ts` if not already present
  - [x] Token stored in `$state` rune — never localStorage, never sessionStorage

- [x] Task 9: Backend — Tests (AC: #1, #3, #4)
  - [x] `tests/auth/test_router.py`: POST `/auth/register` → 201, user in DB, consent_log in DB, token returned
  - [x] `tests/auth/test_router.py`: POST `/auth/register` duplicate email → 409 RFC 7807
  - [x] `tests/auth/test_router.py`: POST `/auth/register` missing consent (gdpr_consent=false) → 422
  - [x] `tests/auth/test_router.py`: POST `/auth/register` password < 8 chars → 422
  - [x] Use `async_db_session` and `test_client` fixtures from `tests/conftest.py`
  - [x] Use `make_user()` factory from `tests/conftest.py` for duplicate email test setup

- [x] Task 10: Frontend — Tests (AC: #2, #5, #6)
  - [x] `src/routes/(auth)/register/+page.test.ts`: submit button disabled without consent checked
  - [x] `src/routes/(auth)/register/+page.test.ts`: blur on invalid email shows inline error
  - [x] `src/routes/(auth)/register/+page.test.ts`: verify keyboard accessibility (axe or vitest-axe)
  - [x] Use `render` and `factories` from `src/lib/test-utils/`

### Review Follow-ups (AI)

- [x] [AI-Review][LOW] Add `Field(min_length=1)` to `privacy_policy_version` in `RegisterRequest` — Pydantic currently accepts empty string `""` [`healthcabinet/backend/app/auth/schemas.py:11`]
- [x] [AI-Review][LOW] Remove email from `DuplicateEmailError` message — logs PII in plaintext; use a generic message and log email as a structured field if needed [`healthcabinet/backend/app/auth/exceptions.py:3`]
- [x] [AI-Review][MED] Update Dev Agent Record File List — 4 files modified in commits but not documented: `healthcabinet/docker-compose.yml`, `healthcabinet/backend/tests/test_health.py`, `.github/workflows/backend-ci.yml`, `healthcabinet/backend/alembic/env.py` [`Dev Agent Record → File List`]
- [x] [AI-Review][MED] Add `RequestValidationError` handler to `main.py` for RFC 7807-compliant 422 responses — FastAPI Pydantic validation errors bypass the `HTTPException` handler and return `{"detail": [...]}` instead of RFC 7807 shape; also fixes frontend displaying `[object Object]` for password-too-short errors since `ApiError.detail` is typed as `string` but receives an array [`healthcabinet/backend/app/main.py`]
- [x] [AI-Review][MED] Change `raise DuplicateEmailError(email) from e` to `raise DuplicateEmailError(email) from None` in service.py — `from e` creates an exception chain with the PII-containing message visible to Sentry and log aggregators; `from None` suppresses the chain (the router already correctly uses `from None`) [`healthcabinet/backend/app/auth/service.py:31`]
- [x] [AI-Review][LOW] Add `consent_log.privacy_policy_version` assertion to `test_register_success` — AC#3 requires `privacy_policy_version` stored in consent_log but test does not verify the value [`healthcabinet/backend/tests/auth/test_router.py:37`]
- [x] [AI-Review][LOW] Replace hardcoded `'1.0'` privacy policy version with a config constant — any version bump requires a frontend code change; extract to an env var or shared constant [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:46`]
- [x] [AI-Review][LOW] Add inline password feedback — no blur-time validation for password length (min 8 chars / 72 bytes); user discovers requirement only after a server round-trip; add a helper text or blur validator [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte`]
- [x] [AI-Review][MED] Update File List — `healthcabinet/frontend/package.json` and `healthcabinet/frontend/package-lock.json` modified in round 2 commit (added `axe-core` dependency) but not documented [`Dev Agent Record → File List`]
- [x] [AI-Review][MED] Fix `ApiError.detail` type — typed as `string` but `validation_exception_handler` returns `exc.errors()` (array of dicts); `formError` renders as `[object Object],[object Object]` for any 422 that reaches the catch block; update interface to `detail?: string | Array<Record<string, unknown>>` and add array handling in catch [`healthcabinet/frontend/src/lib/api/client.ts:13`]
- [x] [AI-Review][LOW] Add RFC 7807 shape assertions to 422 tests — `test_register_gdpr_consent_required` and `test_register_password_too_short` only assert `status_code == 422`; new `validation_exception_handler` is untested; add assertions for `type`, `title`, `status`, `instance` fields [`healthcabinet/backend/tests/auth/test_router.py:74`]
- [x] [AI-Review][LOW] Remove `self.email` attribute from `DuplicateEmailError` — message is now generic but `self.email = email` persists on the object; Sentry serialises exception attributes into event payload exposing PII; either drop the attribute entirely or suppress it from serialisation [`healthcabinet/backend/app/auth/exceptions.py:3`]
- [x] [AI-Review][LOW] Fix password submit-time validation — `handleSubmit` never calls `validatePassword()` and never clears `passwordError`; (1) call `validatePassword()` on submit and return early if invalid; (2) clear `passwordError` before the API call alongside `emailError = ''` [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:43`]
- [x] [AI-Review][LOW] Add 72-byte UTF-8 check to `validatePassword()` — currently only checks `length < 8` (character count); a 25-char multi-byte password (e.g. 25 × "あ" = 75 bytes) passes frontend silently but is rejected by the backend with a 422; add `new TextEncoder().encode(password).length > 72` check [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:32`]
- [x] [AI-Review][LOW] Add test for password blur validation — `+page.test.ts` has no coverage for `validatePassword()`; add `test('password blur shows inline error for short password')` mirroring the existing email blur test [`healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts`]
- [x] [AI-Review][LOW] `PRIVACY_POLICY_VERSION` in `constants.ts` and `config.py` are independent — backend version is env-overridable but frontend hardcodes `'1.0'`; if backend version is bumped via env, consent logs silently record mismatched versions; consider exposing backend version via a `/api/v1/config` endpoint or accept the two-source-of-truth as a known limitation [`healthcabinet/frontend/src/lib/constants.ts:1`]
- [x] [AI-Review][LOW] Remove unused `email` parameter from `DuplicateEmailError.__init__` — accepted but silently dropped; either change signature to `def __init__(self) -> None` and update callers in `service.py` (lines 18, 31) to `raise DuplicateEmailError()`, or add a comment explaining the intentional discard [`healthcabinet/backend/app/auth/exceptions.py:2`]
- [x] [AI-Review][LOW] Add RFC 7807 assertions to remaining 422 tests — `test_register_password_too_long` and `test_register_password_too_long_utf8` still only assert `status_code == 422`; add `type`, `title`, `status`, `instance` assertions to match the two tests fixed in round 3 [`healthcabinet/backend/tests/auth/test_router.py:102`]
- [x] [AI-Review][LOW] Clear `formError` before validation on submit — if a prior API error set `formError`, re-submitting with an invalid email triggers early return without clearing `formError`; user sees stale API error alongside inline email error; move `formError = ''` to before `validateEmail()` in `handleSubmit` [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:41`]
- [x] [AI-Review][LOW] Restore empty-field guard in `validatePassword()` for blur — current `if (!password || ...)` fires error on a pristine untouched field when user tabs through; use `if (password && password.length < 8)` / `if (password && new TextEncoder()...)` for blur, reserve full validation (including empty check) for the submit path [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:32`]
- [x] [AI-Review][LOW] Add test for 72-byte password frontend validation — `validatePassword()` 72-byte branch is untested; add `test('password blur shows error for overlong multi-byte password')` using `'あ'.repeat(25)` (75 bytes, only 25 chars) [`healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts`]
- [x] [AI-Review][LOW] Add backend test for empty `privacy_policy_version` — `Field(min_length=1)` constraint added but no test sends `""` and asserts 422 with RFC 7807 shape [`healthcabinet/backend/tests/auth/test_router.py`]

## Dev Notes

### Critical Architecture Rules (MUST FOLLOW — Enforced by Ruff + CI)

1. **Layer separation** — violations block CI:
   - `router.py` → routes + HTTP concerns only; no DB calls, no business logic
   - `service.py` → business logic only; no direct DB calls; call repository only
   - `repository.py` → all DB reads/writes; no business logic

2. **Encryption boundary** — NOT applicable to this story (no health data written). Do NOT call `encrypt_bytes()` in registration flow. User's hashed password via bcrypt is NOT the same as the app-level AES encryption.

3. **user_id source** — Registration does NOT use `Depends(get_current_user)` (public endpoint). After creation, `user_id` comes from the newly created User object returned by repository. For all subsequent authenticated endpoints, ONLY `Depends(get_current_user)`.

4. **RFC 7807 error shape** — global handler in `app/main.py` already converts `HTTPException` to RFC 7807. Raise `HTTPException(status_code=409, detail="An account with this email already exists")` and the handler will format correctly.

5. **No DB calls in router.py** — router calls `service.register_user()`; service calls repository. Do not shortcut.

### Files to Modify (All Exist as Placeholders from Story 1.1)

**Backend (implement, do NOT restructure):**
- `backend/app/auth/router.py` — add `POST /auth/register` endpoint
- `backend/app/auth/service.py` — add `register_user()` function
- `backend/app/auth/repository.py` — add `create_user()`, `get_user_by_email()`, `create_consent_log()`
- `backend/app/auth/schemas.py` — add `RegisterRequest`, `RegisterResponse`
- `backend/app/core/security.py` — add `create_refresh_token()` if absent (check first)
- `backend/app/auth/exceptions.py` — create; add `DuplicateEmailError`

**Frontend (implement, do NOT restructure):**
- `frontend/src/routes/(auth)/register/+page.svelte` — full implementation
- `frontend/src/lib/api/auth.ts` — add `register()` function
- `frontend/src/lib/stores/auth.svelte.ts` — add `setAccessToken()` if absent

**New test files (create):**
- `backend/tests/auth/test_router.py`
- `frontend/src/routes/(auth)/register/+page.test.ts`

### DB Schema (Already Migrated — Do NOT Create New Migration)

Migration `001_initial_schema.py` already created both tables. Zero schema changes needed for this story.

```sql
-- users table (exists)
users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL UNIQUE,
  hashed_password TEXT NOT NULL,
  role            TEXT NOT NULL DEFAULT 'user',
  tier            TEXT NOT NULL DEFAULT 'free',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
)

-- consent_logs table (exists)
consent_logs (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  consent_type           TEXT NOT NULL,        -- use: "health_data_processing"
  privacy_policy_version TEXT NOT NULL,        -- use: "1.0" (or from Settings if configured)
  consented_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### API Contract

```
POST /auth/register
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "min8chars",
  "gdpr_consent": true,           ← Pydantic must validate true (not just bool)
  "privacy_policy_version": "1.0"
}

Response 201:
{
  "id": "uuid",
  "email": "user@example.com",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000

Response 409 (RFC 7807):
{
  "type": "about:blank",
  "title": "Conflict",
  "status": 409,
  "detail": "An account with this email already exists"
}

Response 422 (Pydantic — gdpr_consent=false or password too short or invalid email):
{
  "type": "about:blank",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": [...]
}
```

### Security Patterns

- **Password hashing**: `hash_password(plaintext)` already implemented in `app/core/security.py` via `passlib[bcrypt]`. Do NOT use bcrypt directly.
- **JWT**: `create_access_token(data={"sub": str(user.id)})` already in `app/core/security.py`. Access token: 15 min.
- **Refresh token**: 30-day expiry, stored in `httpOnly; Secure; SameSite=Strict` cookie. User's access token in JS memory only (never cookie, never localStorage).
- **Consent atomicity**: Create user and consent_log in the same SQLAlchemy transaction. If consent_log creation fails, user creation must roll back.

### Frontend Patterns (Svelte 5 Runes)

```typescript
// Pattern for registration form state (use $state rune)
let email = $state('');
let password = $state('');
let passwordConfirm = $state('');
let consentChecked = $state(false);
let emailError = $state('');
let apiError = $state('');
let isSubmitting = $state(false);

// Blur handler — validate email format inline
function onEmailBlur() {
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    emailError = 'Please enter a valid email address';
  } else {
    emailError = '';
  }
}
```

- Submit button: `<Button disabled={!consentChecked || isSubmitting}>Create Account</Button>`
- Use `use:enhance` from `$app/forms` OR call API directly via `src/lib/api/auth.ts` — choose one pattern consistently; direct API call recommended for SPA flow
- After success: `authStore.setAccessToken(token)` then `goto('/onboarding')`
- Error display below email for 409: `<p class="text-sm text-destructive" id="email-error">{apiError}</p>`, with `aria-describedby="email-error"` on email input

### Previous Story Intelligence (Story 1.1 Learnings)

- **Ruff B008 disabled globally** — `Depends()` in function signatures works. Check `pyproject.toml` for `[tool.ruff.lint] ignore = ["B008"]`.
- **structlog `add_logger_name` removed** — do NOT add it back; use structlog without this processor.
- **Alembic async** — `env.py` uses `run_async_migrations()` with `asyncio.run()`. Do NOT change env.py.
- **SvelteKit not scriptable** — all scaffolding done manually. Files exist, implement them in place.
- **shadcn-svelte CSS** — variables defined in `src/app.css` with `@import "tailwindcss"` (Tailwind v4 syntax). Do not use `@tailwind` directives.
- **Frontend test setup** — `src/lib/test-utils/render.ts` and `factories.ts` exist as empty placeholders. Add test helpers there, don't create new test utility files.
- **`tests/conftest.py` has** `async_db_session`, `test_client` (httpx.AsyncClient), `make_user()` factory — use these, don't recreate.
- **8 existing tests pass** — do NOT modify `tests/core/test_encryption.py` or `tests/test_health.py`.

### Testing Requirements

**Backend — minimum required tests:**
```python
# tests/auth/test_router.py
async def test_register_success(test_client, async_db_session): ...
  # POST /auth/register → 201, access_token present, consent_log row created

async def test_register_duplicate_email(test_client, async_db_session): ...
  # Setup: make_user(email="same@example.com")
  # POST /auth/register same email → 409, detail matches expected string

async def test_register_gdpr_consent_required(test_client): ...
  # POST with gdpr_consent=false → 422

async def test_register_password_too_short(test_client): ...
  # POST with password="short" → 422
```

**Frontend — minimum required tests:**
```typescript
// src/routes/(auth)/register/+page.test.ts
test('submit button disabled when consent unchecked')
test('email blur shows inline error for invalid format')
test('form is accessible via keyboard (axe audit)')
```

### Project Structure Notes

- All backend files are at `healthcabinet/backend/app/...` within the monorepo
- All frontend files are at `healthcabinet/frontend/src/...`
- The monorepo root is at `healthcabinet/` — confirm actual path in your working directory
- `ConsentLog` SQLAlchemy model: check `app/users/models.py` (per architecture, UserProfile and ConsentLog live here). If model not yet defined, add it there — do NOT create a separate model in `app/auth/`.

### References

- Story requirements and BDD criteria: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- Functional requirements FR1, FR30, FR31: [Source: _bmad-output/planning-artifacts/epics.md#Epic 1]
- Auth architecture decisions (JWT, bcrypt, refresh cookie): [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Layer separation enforcement: [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines]
- RFC 7807 error pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns]
- FR mapping to `app/auth/` + `app/users/`: [Source: _bmad-output/planning-artifacts/architecture.md#FR Categories → Structural Mapping]
- DB schema (users + consent_logs): [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- Frontend form patterns (runes, shadcn-svelte): [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- WCAG AA requirement (color + text): [Source: _bmad-output/planning-artifacts/architecture.md#Requirements Overview]
- Test placement convention: [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns]
- Previous story patterns: [Source: _bmad-output/implementation-artifacts/1-1-monorepo-scaffold-infrastructure-baseline.md#Dev Agent Record]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- **Code review round 4 fixes applied (2026-03-20):** All 6 Round 3 review findings addressed:
  - LOW1: `DuplicateEmailError.__init__` signature changed to `def __init__(self) -> None`; callers in `service.py` updated to `raise DuplicateEmailError()`
  - LOW2: RFC 7807 shape assertions added to `test_register_password_too_long` and `test_register_password_too_long_utf8`
  - LOW3: `formError = ''` moved to before `validateEmail()` in `handleSubmit` — prevents stale API error showing alongside inline field errors
  - LOW4: Blur and submit validation split: `validatePasswordBlur()` skips pristine empty field; `validatePasswordSubmit()` enforces empty check on submit
  - LOW5: `test('password blur shows error for overlong multi-byte password')` added using `'あ'.repeat(25)`
  - LOW6: `test_register_empty_privacy_policy_version` added — sends `""` and asserts RFC 7807 422 shape

- **Code review round 3 fixes applied (2026-03-20):** All 8 Round 2 review findings addressed:
  - MED1: File List updated with `package.json`, `package-lock.json`, `client.ts`
  - MED2: `ApiError.detail` typed as `string | Array<Record<string, unknown>>`; catch block now renders user-friendly message for array detail instead of `[object Object]`
  - LOW1: `test_register_gdpr_consent_required` and `test_register_password_too_short` now assert full RFC 7807 shape (`type`, `title`, `status`, `detail`, `instance`)
  - LOW2: `self.email` attribute removed from `DuplicateEmailError` — PII no longer serialised by Sentry
  - LOW3: `handleSubmit` now calls `validatePassword()` and returns early if invalid; clears `passwordError` before API call
  - LOW4: `validatePassword()` now checks `TextEncoder().encode(password).length > 72` for multi-byte passwords
  - LOW5: `+page.test.ts` has new `test('password blur shows inline error for short password')`
  - LOW6: `PRIVACY_POLICY_VERSION` dual source-of-truth accepted as known limitation; documented

- **Code review fixes applied (2026-03-20):** All 8 review findings addressed:
  - MED1: File List updated — 4 missing files (docker-compose.yml, test_health.py, backend-ci.yml, alembic/env.py) already present, checkboxes marked
  - MED2: Added `RequestValidationError` handler to `main.py` — 422 Pydantic errors now return RFC 7807 shape with `type/title/status/detail/instance`; fixes `[object Object]` display bug in frontend
  - MED3: Changed `from e` → `from None` in `service.py:31` — suppresses PII exception chain from Sentry/log aggregators
  - LOW1: Added `Field(min_length=1)` to `privacy_policy_version` in `schemas.py` — rejects empty string `""`
  - LOW2: `DuplicateEmailError.__init__` now stores `email` as attribute but omits it from message string — generic message prevents PII leak in logs
  - LOW3: `test_register_success` now asserts `consent_log.privacy_policy_version == "1.0"` per AC#3
  - LOW4: Created `frontend/src/lib/constants.ts` with `PRIVACY_POLICY_VERSION = '1.0'`; `+page.svelte` imports and uses it
  - LOW5: Added `validatePassword()` blur handler + inline error below password field in `+page.svelte`; password error tracked in `$state`

- **Code review fixes applied (2026-03-19):**
  - H1: Fixed backwards model imports across repository.py, service.py, conftest.py, test_router.py — `User` lives in `app.auth.models`, `ConsentLog` in `app.users.models`
  - H2: Fixed RFC 7807 `title` field in main.py — now returns HTTP reason phrase (e.g., "Conflict") not the detail string
  - H3: Fixed +page.svelte to call `authStore.setAccessToken()` instead of directly calling internal `tokenState.setToken()`
  - H4: Fixed `REFRESH_TOKEN_EXPIRE_DAYS` from 7 → 30 in security.py (cookie was already 30 days, JWT was wrong)
  - H5: Fixed `ACCESS_TOKEN_EXPIRE_MINUTES` from 30 → 15 in security.py (security boundary per spec)
  - M1: Fixed frontend blur test to enter invalid email before blur — was testing empty field instead of invalid format
  - M2: Wrapped user + consent_log creation in `db.begin_nested()` savepoint for explicit atomicity
  - M3: Fixed `test_register_success` to assert consent_log by `user_id` and verify user DB row; was filtering by `privacy_policy_version` (non-unique)

### File List

- `healthcabinet/backend/app/auth/schemas.py`
- `healthcabinet/backend/app/auth/exceptions.py`
- `healthcabinet/backend/app/auth/repository.py`
- `healthcabinet/backend/app/auth/service.py`
- `healthcabinet/backend/app/auth/router.py`
- `healthcabinet/backend/app/main.py`
- `healthcabinet/backend/tests/conftest.py`
- `healthcabinet/backend/tests/auth/__init__.py`
- `healthcabinet/backend/tests/auth/test_router.py`
- `healthcabinet/frontend/src/lib/api/auth.ts`
- `healthcabinet/frontend/src/lib/stores/auth.svelte.ts`
- `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte`
- `healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts`
- `healthcabinet/docker-compose.yml`
- `healthcabinet/backend/tests/test_health.py`
- `.github/workflows/backend-ci.yml`
- `healthcabinet/backend/alembic/env.py`
- `healthcabinet/backend/app/core/config.py`
- `healthcabinet/frontend/src/lib/constants.ts`
- `healthcabinet/frontend/package.json`
- `healthcabinet/frontend/package-lock.json`
- `healthcabinet/frontend/src/lib/api/client.ts`

## Change Log

- 2026-03-19: Initial implementation — all 10 tasks completed (backend schemas, repo, service, router, frontend page, auth store, API client, tests)
- 2026-03-19: Code review round 1 fixes — 8 items (H1–H5 high/med, M1–M3 med) addressing model imports, RFC 7807 title, auth store call, token expiry values, test correctness, atomicity
- 2026-03-20: Code review round 2 fixes — 8 items resolved: RFC 7807 for 422 errors, PII suppression in exception chain, `privacy_policy_version` min_length validation, PII removed from error message, test assertion for `privacy_policy_version`, constants file for privacy policy version, inline password blur validation
- 2026-03-20: Code review round 3 fixes — 8 items resolved: `ApiError.detail` type union, 422 RFC 7807 test assertions, `self.email` PII removed from exception, submit-time password validation, 72-byte UTF-8 check, password blur test, file list updated
- 2026-03-20: Code review round 4 fixes — 6 items resolved: `DuplicateEmailError` signature cleaned, RFC 7807 assertions on all remaining 422 tests, stale `formError` cleared before validators, blur/submit validation split, 72-byte test added, empty `privacy_policy_version` backend test added

## Senior Developer Review (AI)

**Review Date:** 2026-03-20 (Round 2)
**Reviewer:** claude-sonnet-4-6
**Outcome:** Changes Requested

### Summary

Round 2 fixes correctly addressed all 8 prior action items. `RequestValidationError` handler is properly implemented, PII exception chain is suppressed, `privacy_policy_version` validation is in place, and the constants refactor is clean. New issues: `ApiError.detail` type mismatch means 422 errors still display incorrectly in edge cases, `package.json`/`package-lock.json` are undocumented, and the new `validatePassword()` has incomplete logic (not called on submit, no 72-byte check, no test coverage).

### Round 1 Action Items (2026-03-20)

- [x] [MED] Update File List — 4 files changed in commits but not documented [`Dev Agent Record → File List`]
- [x] [MED] Add `RequestValidationError` handler to `main.py` for RFC 7807-compliant 422 responses [`healthcabinet/backend/app/main.py`]
- [x] [MED] Change `from e` → `from None` in `raise DuplicateEmailError(email) from e` to suppress PII exception chain [`healthcabinet/backend/app/auth/service.py:31`]
- [x] [LOW] Add `Field(min_length=1)` to `privacy_policy_version` [`healthcabinet/backend/app/auth/schemas.py:14`]
- [x] [LOW] Remove email from `DuplicateEmailError` message [`healthcabinet/backend/app/auth/exceptions.py:3`]
- [x] [LOW] Assert `consent_log.privacy_policy_version` in `test_register_success` [`healthcabinet/backend/tests/auth/test_router.py:37`]
- [x] [LOW] Replace hardcoded `'1.0'` privacy policy version with config constant [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:46`]
- [x] [LOW] Add inline password length feedback on blur [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte`]

### Round 2 Action Items (2026-03-20)

- [x] [MED] Update File List — `package.json` and `package-lock.json` modified (added `axe-core`) but not documented [`Dev Agent Record → File List`]
- [x] [MED] Fix `ApiError.detail` type — typed `string` but 422 returns array; `formError` renders `[object Object]` [`healthcabinet/frontend/src/lib/api/client.ts:13`]
- [x] [LOW] Add RFC 7807 shape assertions to 422 tests [`healthcabinet/backend/tests/auth/test_router.py:74`]
- [x] [LOW] Remove `self.email` attribute from `DuplicateEmailError` — PII still accessible to Sentry attribute serialisation [`healthcabinet/backend/app/auth/exceptions.py:3`]
- [x] [LOW] Fix password submit-time validation — call `validatePassword()` on submit and clear `passwordError` [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:43`]
- [x] [LOW] Add 72-byte UTF-8 check to `validatePassword()` [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:32`]
- [x] [LOW] Add test for password blur validation [`healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts`]
- [x] [LOW] `PRIVACY_POLICY_VERSION` in `constants.ts` and `config.py` are independent sources of truth — accepted as known limitation; a `/api/v1/config` endpoint is future work [`healthcabinet/frontend/src/lib/constants.ts:1`]

### Round 3 Action Items (2026-03-20)

- [x] [LOW] Remove unused `email` parameter from `DuplicateEmailError.__init__` [`healthcabinet/backend/app/auth/exceptions.py:2`]
- [x] [LOW] Add RFC 7807 assertions to `test_register_password_too_long` and `test_register_password_too_long_utf8` [`healthcabinet/backend/tests/auth/test_router.py:102`]
- [x] [LOW] Clear `formError` before validators in `handleSubmit` to prevent stale error display [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:41`]
- [x] [LOW] Restore empty-field guard in `validatePassword()` for blur path only [`healthcabinet/frontend/src/routes/(auth)/register/+page.svelte:32`]
- [x] [LOW] Add test for 72-byte overlong password in `+page.test.ts` [`healthcabinet/frontend/src/routes/(auth)/register/+page.test.ts`]
- [x] [LOW] Add backend test for empty `privacy_policy_version` → 422 RFC 7807 [`healthcabinet/backend/tests/auth/test_router.py`]
