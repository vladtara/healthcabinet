# Story 1.4: Medical Profile Setup

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an authenticated user,
I want to complete my medical profile with age, sex, height, weight, known conditions, medications, and family history,
so that HealthCabinet can generate a personalized health baseline and relevant recommendations from day one.

## Acceptance Criteria

1. **Given** a newly registered user is redirected to onboarding **When** they land on `/onboarding` **Then** a step progress indicator is visible showing "Step N of M" **And** a Back button is available on all steps after step 1

2. **Given** a user completes the onboarding profile form **When** they submit valid profile data **Then** a `user_profiles` record is created/updated with: `age`, `sex`, `height_cm`, `weight_kg`, `known_conditions` (array), `medications` (array), `family_history` (text) **And** the user is redirected to `/dashboard`

3. **Given** a user enters their known conditions **When** they interact with the conditions field **Then** a multi-select chip interface is presented (not a dropdown) allowing multiple condition selection **And** a free-text "other condition" input is available for conditions not in the preset list

4. **Given** a user navigates away from onboarding without completing all steps **When** they return to the app **Then** onboarding resumes from the last incomplete step

5. **Given** an authenticated user navigates to `/settings` **When** they edit their medical profile **Then** all profile fields are pre-populated with current values **And** changes are saved via `PUT /users/me/profile` **And** a success toast notification appears: "Profile updated"

6. **Given** the profile form is rendered **When** a keyboard-only user navigates **Then** all form fields are reachable via Tab and all interactive elements operable via keyboard **And** inline validation errors appear on blur with color + text label (never color alone)

## Tasks / Subtasks

- [x] Task 1: Backend — Alembic migration for `user_profiles` table (AC: #2)
  - [x] Create `backend/alembic/versions/002_user_profiles.py`
  - [x] Add `user_profiles` table (see schema below)
  - [x] Run migration against local DB: `alembic upgrade head`
  - [x] Do NOT modify `001_initial_schema.py` — add a new migration only

- [x] Task 2: Backend — `UserProfile` SQLAlchemy model (AC: #2)
  - [x] Add `UserProfile` ORM model to `backend/app/users/models.py` (check what's already there)
  - [x] Map all columns: `id`, `user_id` (FK → users.id, CASCADE), `age`, `sex`, `height_cm`, `weight_kg`, `known_conditions` (JSONB), `medications` (JSONB), `family_history`, `onboarding_step`, `created_at`, `updated_at`
  - [x] Import `UserProfile` into `app/users/__init__.py` if applicable

- [x] Task 3: Backend — Profile schemas (AC: #2, #5)
  - [x] Add `ProfileUpdateRequest` Pydantic model to `backend/app/users/schemas.py`:
    - `age: int | None` (1–120 range validator)
    - `sex: Literal["male", "female", "other", "prefer_not_to_say"] | None`
    - `height_cm: float | None` (50–300 range)
    - `weight_kg: float | None` (10–500 range)
    - `known_conditions: list[str] | None` (max 50 items)
    - `medications: list[str] | None` (max 50 items)
    - `family_history: str | None` (max 2000 chars)
    - `onboarding_step: int | None` (1–10)
  - [x] Add `ProfileResponse` Pydantic model: all fields above + `id: UUID`, `user_id: UUID`, `created_at`, `updated_at`

- [x] Task 4: Backend — Repository layer (AC: #2, #5)
  - [x] Implement `get_user_profile(db, user_id: UUID) -> UserProfile | None` in `backend/app/users/repository.py`
  - [x] Implement `upsert_user_profile(db, user_id: UUID, **fields) -> UserProfile`:
    - Use INSERT ... ON CONFLICT (user_id) DO UPDATE (PostgreSQL upsert)
    - Set `updated_at = NOW()` on update
  - [x] Implement `update_onboarding_step(db, user_id: UUID, step: int) -> UserProfile`

- [x] Task 5: Backend — Service layer (AC: #2, #4, #5)
  - [x] Implement `get_profile(db, user_id: UUID) -> UserProfile | None` in `backend/app/users/service.py`
  - [x] Implement `update_profile(db, user_id: UUID, data: ProfileUpdateRequest) -> UserProfile`:
    - Call `upsert_user_profile` with non-null fields from request
    - Return updated profile
  - [x] Implement `save_onboarding_progress(db, user_id: UUID, step: int) -> UserProfile`

- [x] Task 6: Backend — Router (AC: #2, #5)
  - [x] Add `GET /users/me/profile` to `backend/app/users/router.py`:
    - Requires `current_user = Depends(get_current_user)`
    - Returns `ProfileResponse` or 404 if not yet created
  - [x] Add `PUT /users/me/profile` to `backend/app/users/router.py`:
    - Requires `current_user = Depends(get_current_user)`
    - Body: `ProfileUpdateRequest`
    - Returns `ProfileResponse` with 200
  - [x] Add `PATCH /users/me/onboarding-step` for saving progress:
    - Body: `{"step": N}`
    - Returns 200

- [x] Task 7: Backend — Wire router into main.py (AC: #2)
  - [x] In `backend/app/main.py`, **uncomment** lines 124–131 (the users router is already written but commented out):
    ```python
    from app.users.router import router as users_router
    # ...
    app.include_router(users_router, prefix="/api/v1")
    ```
  - [x] The router itself in `users/router.py` should declare `router = APIRouter(prefix="/users", tags=["users"])` — `main.py` adds the `/api/v1` wrapper, making all endpoints resolve to `/api/v1/users/...`
  - [x] Do NOT change any other router registrations in main.py

- [x] Task 8: Frontend — TypeScript types (AC: #2, #5)
  - [x] Add `UserProfile` interface to the **existing** `frontend/src/lib/types/api.ts` (do NOT create `types/users.ts` — all API types live in `types/api.ts` per the pattern from Stories 1.1–1.3):
    ```typescript
    export interface UserProfile {
      id: string;
      user_id: string;
      age: number | null;
      sex: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null;
      height_cm: number | null;
      weight_kg: number | null;
      known_conditions: string[];
      medications: string[];
      family_history: string | null;
      onboarding_step: number;
      created_at: string;
      updated_at: string;
    }
    ```

- [x] Task 9: Frontend — API client functions (AC: #2, #5)
  - [x] Create `frontend/src/lib/api/users.ts` with:
    ```typescript
    import { apiFetch } from '$lib/api/client.svelte';
    import type { UserProfile } from '$lib/types/api';

    export async function getProfile(): Promise<UserProfile | null> {
      return apiFetch<UserProfile>('/api/v1/users/me/profile').catch(() => null);
    }

    export async function updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
      return apiFetch<UserProfile>('/api/v1/users/me/profile', { method: 'PUT', body: JSON.stringify(data) });
    }

    export async function saveOnboardingStep(step: number): Promise<void> {
      return apiFetch<void>('/api/v1/users/me/onboarding-step', { method: 'PATCH', body: JSON.stringify({ step }) });
    }
    ```
  - [x] Use `apiFetch` from `$lib/api/client.svelte` — NOT `fetchWithAuth` or `client.ts` (those do not exist)

- [x] Task 10: Frontend — Onboarding page (AC: #1, #2, #3, #4, #6)
  - [x] Extend the **existing stub** at `frontend/src/routes/(app)/onboarding/+page.svelte` — file already exists with a `<script>` comment placeholder; replace stub content with full implementation using Svelte 5 runes
  - [x] Multi-step structure (3 steps):
    - **Step 1:** Basic info — age (number input), sex (radio group: Male / Female / Other / Prefer not to say), height (number input in cm), weight (number input in kg)
    - **Step 2:** Health conditions — multi-select chip interface for preset conditions + free-text "Other" input; medications (tag-input or textarea)
    - **Step 3:** Family history — textarea (optional, max 2000 chars)
  - [x] Step progress indicator: "Step 1 of 3", "Step 2 of 3", "Step 3 of 3"
  - [x] Back button visible on steps 2 and 3
  - [x] On step change: call `saveOnboardingStep(currentStep)` → persists progress
  - [x] On load: fetch existing profile via `getProfile()` → if `onboarding_step > 1`, resume from that step (pre-populate fields)
  - [x] On final submit: call `updateProfile(allData)` → redirect to `/dashboard`
  - [x] Known conditions preset list (chip multi-select):
    ```
    ['Type 2 Diabetes', 'Hypertension', 'Hypothyroidism', 'Hashimoto\'s',
     'Hyperthyroidism', 'High Cholesterol', 'Asthma', 'PCOS', 'Anemia',
     'Cardiovascular Disease', 'Kidney Disease', 'Liver Disease']
    ```
  - [x] Chips: clicking toggles selection; selected chips visually distinct (filled) from unselected
  - [x] "Other condition" free-text: input + "Add" button → adds to the selected list as a custom chip
  - [x] Use shadcn-svelte: `Input`, `Button`, `Label`, `Textarea`, `RadioGroup`, `RadioGroupItem`
  - [x] All fields keyboard-accessible (Tab through all inputs, space toggles chips, Enter adds "Other")

- [x] Task 11: Frontend — Settings profile edit section (AC: #5, #6)
  - [x] Extend the **existing stub** at `frontend/src/routes/(app)/settings/+page.svelte` — file already exists with a `<script>` comment placeholder; replace stub content with full implementation
  - [x] On load: `GET /users/me/profile` → pre-populate all fields
  - [x] Same field components as onboarding but in single-page layout (no steps)
  - [x] On save: `PUT /users/me/profile` → show success toast "Profile updated"
  - [x] Use Svelte Query `createMutation` for the save action (TanStack Query for Svelte uses `createMutation`/`createQuery` — NOT `useMutation`/`useQuery` which are React-only)
  - [x] Toast: use shadcn-svelte Sonner or equivalent toast primitive

- [x] Task 12: Backend — Tests (AC: #2, #5)
  - [x] `tests/users/test_router.py`:
    - `test_get_profile_not_found`: `GET /users/me/profile` before creating → 404
    - `test_get_profile_success`: create profile, then `GET /users/me/profile` → 200 with correct data
    - `test_update_profile_creates_new`: `PUT /users/me/profile` for new user → 200, profile in DB
    - `test_update_profile_upserts`: `PUT /users/me/profile` twice → 200, no duplicate record
    - `test_update_profile_partial`: `PUT /users/me/profile` with only `age` → only age updated, others unchanged
    - `test_profile_requires_auth`: `GET /users/me/profile` without token → 401
    - `test_profile_user_isolation`: User A cannot see User B's profile (user_id from get_current_user)
  - [x] Use `make_user()` and `async_db_session` from `tests/conftest.py`
  - [x] Create `tests/users/` directory if it doesn't exist

- [x] Task 13: Frontend — Tests (AC: #1, #3, #6)
  - [x] `src/routes/(app)/onboarding/+page.test.ts`:
    - `test('step indicator shows correct step number')`
    - `test('back button absent on step 1, present on steps 2 and 3')`
    - `test('chip multi-select toggles condition selection')`
    - `test('other condition input adds custom chip')`
    - `test('all form fields keyboard accessible - axe audit')`

## Dev Notes

### Sequential Dependency on Story 1.3

**This story (1-4) MUST follow Story 1.3 (Login).** All endpoints use `Depends(get_current_user)` which is implemented in 1-3. Do not start frontend development until 1-3's auth store and token refresh interceptor are in place. Backend development can begin in parallel since the `get_current_user` dependency exists as a placeholder in `app/auth/dependencies.py`.

### Critical Architecture Rules (MUST FOLLOW — Enforced by Ruff + CI)

1. **user_id source** — ALWAYS from `Depends(get_current_user)`. The profile endpoint must NEVER accept `user_id` from the request body. A user cannot read or write another user's profile.

2. **Layer separation** — violations block CI:
   - `router.py` → routes + HTTP; calls service only
   - `service.py` → business logic; calls repository only
   - `repository.py` → DB reads/writes; no business logic

3. **Encryption boundary** — NOT applicable to this story. Medical profile fields are stored plaintext in `user_profiles`. Health data encryption (AES-256-GCM) applies to `health_values` only. Do NOT apply `encrypt_bytes()` to profile data.

4. **JSONB for array fields** — `known_conditions` and `medications` are stored as JSONB arrays in PostgreSQL. Use SQLAlchemy's `JSONB` type. Frontend sends them as JSON arrays; Pydantic validates as `list[str]`.

5. **RFC 7807 errors** — global handler already wired. Raise `HTTPException` and let the handler format it.

6. **Onboarding step persistence** — `onboarding_step` column tracks multi-step progress. Value 1–3 = current step; value 3 (completed) means all steps done. When user completes step 3 and submits, do NOT reset `onboarding_step` to 0 — leave at 3 to signal completion.

### Files to Create/Modify

**Backend:**
- `backend/alembic/versions/002_user_profiles.py` — NEW migration
- `backend/app/users/models.py` — add `UserProfile` model
- `backend/app/users/schemas.py` — add `ProfileUpdateRequest`, `ProfileResponse`
- `backend/app/users/repository.py` — add profile CRUD functions
- `backend/app/users/service.py` — add profile service functions
- `backend/app/users/router.py` — add GET + PUT profile endpoints
- `backend/app/main.py` — verify `/users` router is included

**Frontend:**
- `frontend/src/lib/types/api.ts` — EXTEND existing file (add `UserProfile` interface; do NOT create `types/users.ts`)
- `frontend/src/lib/api/users.ts` — NEW file (profile API functions using `apiFetch`)
- `frontend/src/routes/(app)/onboarding/+page.svelte` — EXTEND existing stub (already exists, replace placeholder content)
- `frontend/src/routes/(app)/settings/+page.svelte` — EXTEND existing stub (already exists, replace placeholder content)

**New test files:**
- `backend/tests/users/test_router.py`
- `frontend/src/routes/(app)/onboarding/+page.test.ts`

### DB Schema

```sql
-- New migration: 002_user_profiles.py
CREATE TABLE user_profiles (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  age               INTEGER,
  sex               TEXT,            -- 'male' | 'female' | 'other' | 'prefer_not_to_say'
  height_cm         NUMERIC,
  weight_kg         NUMERIC,
  known_conditions  JSONB NOT NULL DEFAULT '[]'::jsonb,
  medications       JSONB NOT NULL DEFAULT '[]'::jsonb,
  family_history    TEXT,
  onboarding_step   INTEGER NOT NULL DEFAULT 1,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
```

**Note:** `UNIQUE` constraint on `user_id` enables `INSERT ... ON CONFLICT (user_id) DO UPDATE` upsert pattern.

### API Contract

```
GET /users/me/profile
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "user_id": "uuid",
  "age": 34,
  "sex": "female",
  "height_cm": 168.0,
  "weight_kg": 65.0,
  "known_conditions": ["Hashimoto's", "Anemia"],
  "medications": ["Levothyroxine 50mcg"],
  "family_history": "Mother: hypertension",
  "onboarding_step": 3,
  "created_at": "2026-03-06T10:00:00Z",
  "updated_at": "2026-03-06T10:05:00Z"
}

Response 404 (profile not yet created):
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Profile not found"
}

---

PUT /users/me/profile
Authorization: Bearer {access_token}
Content-Type: application/json

Request (all fields optional — only included fields updated):
{
  "age": 34,
  "sex": "female",
  "height_cm": 168.0,
  "weight_kg": 65.0,
  "known_conditions": ["Hashimoto's", "Anemia"],
  "medications": ["Levothyroxine 50mcg"],
  "family_history": "Mother: hypertension"
}

Response 200: full ProfileResponse (same as GET)

Response 422: Pydantic validation errors (age out of range, etc.)
```

### UX Patterns

**Multi-select chip component (known_conditions):**
```svelte
<script lang="ts">
  const PRESET_CONDITIONS = [
    'Type 2 Diabetes', 'Hypertension', 'Hypothyroidism', "Hashimoto's",
    'Hyperthyroidism', 'High Cholesterol', 'Asthma', 'PCOS', 'Anemia',
    'Cardiovascular Disease', 'Kidney Disease', 'Liver Disease'
  ];

  let selectedConditions = $state<string[]>([]);
  let otherCondition = $state('');

  function toggleCondition(condition: string) {
    if (selectedConditions.includes(condition)) {
      selectedConditions = selectedConditions.filter(c => c !== condition);
    } else {
      selectedConditions = [...selectedConditions, condition];
    }
  }

  function addOtherCondition() {
    if (otherCondition.trim() && !selectedConditions.includes(otherCondition.trim())) {
      selectedConditions = [...selectedConditions, otherCondition.trim()];
      otherCondition = '';
    }
  }
</script>

{#each PRESET_CONDITIONS as condition}
  <button
    type="button"
    class={selectedConditions.includes(condition) ? 'chip chip-selected' : 'chip'}
    onclick={() => toggleCondition(condition)}
    aria-pressed={selectedConditions.includes(condition)}
  >
    {condition}
  </button>
{/each}

<!-- Other condition input -->
<div class="flex gap-2">
  <Input bind:value={otherCondition} placeholder="Other condition..." />
  <Button type="button" onclick={addOtherCondition}>Add</Button>
</div>
```

**Step progress indicator:**
```svelte
<div role="progressbar" aria-valuenow={currentStep} aria-valuemin={1} aria-valuemax={totalSteps}>
  Step {currentStep} of {totalSteps}
</div>
```

**Onboarding step persistence:**
```typescript
async function goToNextStep() {
  await saveOnboardingStep(currentStep + 1);  // Persist before navigating
  currentStep++;
}
```

### Previous Story Intelligence (Stories 1.1–1.3 Learnings)

- **Ruff B008 disabled globally** — `Depends()` in function signatures works as intended.
- **structlog** — Use instead of `print()`. Do NOT add `add_logger_name` processor.
- **Alembic async** — `env.py` uses `run_async_migrations()`. Do NOT modify; just create new migration files.
- **`make_user()`** factory in `tests/conftest.py` — use for creating test users; add any needed profile factory here too.
- **Token refresh** — `apiFetch()` in `client.svelte.ts` handles 401s and token refresh transparently (established in Story 1.3). Import as `import { apiFetch } from '$lib/api/client.svelte'`. Use for all authenticated API calls. `client.ts` does NOT exist — it was replaced by `client.svelte.ts`.
- **`get_current_user`** — Fully implemented in Story 1.3's `app/auth/dependencies.py`. Import and use directly.
- **shadcn-svelte** — Components in `$lib/components/ui/`. Tailwind v4 with `@import "tailwindcss"` in `src/app.css`.
- **Svelte Query** — Use `createQuery` / `createMutation` from `@tanstack/svelte-query` for server state. Wrap in query client in `(app)/+layout.svelte`.

### Testing Requirements

```python
# tests/users/test_router.py
async def test_get_profile_not_found(test_client, async_db_session):
    user = await make_user(async_db_session)
    token = create_access_token({"sub": str(user.id)})
    response = await test_client.get("/users/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

async def test_update_profile_creates_and_returns(test_client, async_db_session):
    user = await make_user(async_db_session)
    token = create_access_token({"sub": str(user.id)})
    payload = {"age": 34, "sex": "female", "known_conditions": ["Anemia"]}
    response = await test_client.put("/users/me/profile", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 34
    assert data["known_conditions"] == ["Anemia"]
    assert data["user_id"] == str(user.id)  # Must be current user's ID, not from body

async def test_update_profile_upserts_not_duplicates(test_client, async_db_session):
    # Call PUT twice — should only have 1 row in user_profiles
    ...

async def test_profile_user_isolation(test_client, async_db_session):
    # User A cannot read User B's profile
    user_a = await make_user(async_db_session, email="a@test.com")
    user_b = await make_user(async_db_session, email="b@test.com")
    # Create profile for user_b
    # Authenticate as user_a, GET /users/me/profile → 404 (not user_b's data)
    ...

async def test_profile_requires_auth(test_client):
    response = await test_client.get("/users/me/profile")
    assert response.status_code == 401
```

### Project Structure Notes

- `UserProfile` model belongs in `app/users/models.py` — NOT in `app/auth/models.py`
- `ConsentLog` model: lives in `app/users/models.py` per architecture (check if already defined in Story 1.1 or 1.2)
- All backend files at `healthcabinet/backend/app/...`
- All frontend files at `healthcabinet/frontend/src/...`

### References

- Story requirements and BDD criteria: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- Functional requirements FR3: [Source: _bmad-output/planning-artifacts/epics.md#Epic 1]
- UX: multi-select chip, onboarding step progress: [Source: _bmad-output/planning-artifacts/epics.md#UX: Component Requirements]
- Architecture: layer separation enforcement: [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines]
- Architecture: user_id from Depends(get_current_user): [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Architecture: snake_case naming, domain structure: [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- Architecture: RFC 7807 errors: [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns]
- Architecture: WCAG AA (color + text): [Source: _bmad-output/planning-artifacts/architecture.md#Requirements Overview]
- UX: responsive, tablet/mobile breakpoints: [Source: _bmad-output/planning-artifacts/epics.md#UX: Responsive Design]
- UX: keyboard accessibility: [Source: _bmad-output/planning-artifacts/epics.md#UX: Accessibility]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- JSONB `server_default` in ORM model required `text()` wrapper (not raw string) to avoid asyncpg JSON parse error during `metadata.create_all()`
- SQLAlchemy `insert().on_conflict_do_update()` (dialect-specific) used for upsert instead of raw `text()` SQL, ensuring proper JSONB array type serialization via asyncpg
- `make_user` fixture returns `(User, password)` tuple — tests unpack with `user, _ = await make_user()`
- `create_access_token(str(user.id))` — takes plain string subject, not a dict
- `test_profile_requires_auth`: HTTPBearer returns 401 (not 403) when no credentials are provided
- RadioGroup/Textarea not in installed shadcn-svelte components → Textarea created as minimal wrapper; RadioGroup implemented as native HTML radio inputs with Tailwind
- No Sonner toast installed → success message via `role="status"` div with `setTimeout` clear
- `npm run check` (svelte-kit sync) was already failing before this story due to `+page.test.ts` files in auth routes (pre-existing issue from Story 1.3)

### Completion Notes List

- Implemented full `user_profiles` table via Alembic migration 002
- `UserProfile` ORM model with JSONB arrays for known_conditions and medications
- Full backend CRUD: repository (upsert via ON CONFLICT), service, router with GET/PUT/PATCH endpoints
- Users router wired into main.py; endpoints at `/api/v1/users/me/profile`
- Frontend: `UserProfile` type added to api.ts, `users.ts` API client created
- 3-step onboarding page with step progress indicator, chip multi-select, back/next navigation, onboarding step persistence, resume from last step
- Settings page with single-page profile editor using `createMutation`; QueryClientProvider added to `(app)/+layout.svelte`
- Textarea shadcn-style wrapper component created
- 7 backend tests pass (48 total, no regressions); 5 frontend tests pass (21 total, no regressions)
- All ACs satisfied: step indicator (AC1), profile upsert + redirect (AC2), chip multi-select + other input (AC3), step persistence + resume (AC4), settings pre-population + PUT + success message (AC5), keyboard accessibility + aria attributes + error text labels (AC6)

### File List

- healthcabinet/backend/alembic/versions/002_user_profiles.py (NEW)
- healthcabinet/backend/app/users/models.py (modified)
- healthcabinet/backend/app/users/schemas.py (implemented)
- healthcabinet/backend/app/users/repository.py (implemented)
- healthcabinet/backend/app/users/service.py (implemented)
- healthcabinet/backend/app/users/router.py (implemented)
- healthcabinet/backend/app/main.py (modified — users router uncommented)
- healthcabinet/backend/tests/users/__init__.py (NEW)
- healthcabinet/backend/tests/users/test_router.py (NEW)
- healthcabinet/frontend/src/lib/types/api.ts (modified)
- healthcabinet/frontend/src/lib/api/users.ts (NEW)
- healthcabinet/frontend/src/routes/(app)/+layout.svelte (modified — QueryClientProvider)
- healthcabinet/frontend/src/lib/components/ui/textarea/textarea.svelte (NEW)
- healthcabinet/frontend/src/lib/components/ui/textarea/index.ts (NEW)
- healthcabinet/frontend/src/routes/(app)/onboarding/+page.svelte (implemented)
- healthcabinet/frontend/src/routes/(app)/settings/+page.svelte (implemented)
- healthcabinet/frontend/src/routes/(app)/onboarding/+page.test.ts (NEW)

### Change Log

- 2026-03-21: Implemented Story 1.4 — Medical profile setup. Added user_profiles table, full CRUD backend, 3-step onboarding wizard, settings profile editor, 7 backend tests, 5 frontend tests.

### Review Findings

#### Decision-Needed
- [x] [Review][Decision] **onboarding_step writable via PUT /me/profile** — RESOLVED: removed `onboarding_step` from `ProfileUpdateRequest`; frontend `handleSubmit` now calls `saveOnboardingStep(TOTAL_STEPS)` before `updateProfile`. [backend/app/users/schemas.py, frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Decision] **Settings "Profile updated" notification is an inline banner, not a toast** — DEFERRED/ACCEPTED: `role="status"` div with auto-hide is accessible and functional; no Sonner installed. Acceptable at MVP.
- [x] [Review][Decision] **Clearing fields via null is not possible** — RESOLVED: changed `update_profile` to `model_dump(exclude_unset=True)`; clients can now send explicit `null` to clear a field. [backend/app/users/service.py]

#### Patch
- [x] [Review][Patch] **Back button (goToPrevStep) does not persist step regression to backend** — FIXED: `goToPrevStep` now calls `saveOnboardingStep(prev)`. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **Settings page has no inline validation errors on blur** — FIXED: added `handleAgeBlur`, `handleHeightBlur`, `handleWeightBlur` with `aria-invalid`, `aria-describedby`, and error paragraphs. [frontend/src/routes/(app)/settings/+page.svelte]
- [x] [Review][Patch] **No redirect to /dashboard if onboarding already complete** — FIXED: `$effect` now redirects to `/dashboard` if `profile.onboarding_step >= TOTAL_STEPS`. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **No per-item length validation on known_conditions/medications list items** — FIXED: introduced `ConditionStr = Annotated[str, StringConstraints(max_length=200)]`. [backend/app/users/schemas.py]
- [x] [Review][Patch] **Double-click Next button can skip a step** — FIXED: added `isSaving` guard; Next button disabled while save is in-flight. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **No error handling in handleSubmit for updateProfile failure** — FIXED: added `try/catch` with `submitError` state displayed to user. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **upsert_user_profile may return stale ORM data** — FIXED: added `await db.refresh(profile)` after re-select. [backend/app/users/repository.py]
- [x] [Review][Patch] **updated_at has no onupdate in SQLAlchemy model** — FIXED: added `onupdate=func.now()`. [backend/app/users/models.py]
- [x] [Review][Patch] **Duplicate UniqueConstraint on UserProfile.user_id** — FIXED: removed redundant `UniqueConstraint` from `__table_args__`. [backend/app/users/models.py]
- [x] [Review][Patch] **PATCH /me/onboarding-step allows backward step regression** — DISMISSED: conflicts with P5 (back navigation now intentionally persists lower step via `saveOnboardingStep`); backward navigation is expected behavior. [backend/app/users/router.py]
- [x] [Review][Patch] **sex field in ProfileResponse typed as str | None instead of Literal** — FIXED: changed to `Literal["male", "female", "other", "prefer_not_to_say"] | None`. [backend/app/users/schemas.py]
- [x] [Review][Patch] **Onboarding $effect fetch not cancelled on unmount** — FIXED: added `cancelled` flag; returns cleanup function that sets `cancelled = true`. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **updateProfile in users.ts accepts Partial<UserProfile> including readonly fields** — FIXED: introduced `ProfileUpdateData` write-only type; updated `updateProfile` signature and all callers. [frontend/src/lib/api/users.ts]
- [x] [Review][Patch] **onboarding_step clamping: if API returns step > TOTAL_STEPS the UI breaks** — FIXED: `currentStep = Math.min(profile.onboarding_step, TOTAL_STEPS)`. [frontend/src/routes/(app)/onboarding/+page.svelte]
- [x] [Review][Patch] **Step data only submitted on final submit — failed submit loses all entered data** — PARTIALLY ADDRESSED: `handleSubmit` now shows a retry-able error state on failure. Full per-step data persistence deferred as enhancement.
- [x] [Review][Patch] **Custom condition remove button (✕) has no aria-label** — FIXED: added `aria-label="Remove {custom}"` to custom condition chips in both onboarding and settings pages.

#### Deferred
- [x] [Review][Defer] **No +layout.server.ts auth guard for (app)/ routes** [frontend/src/routes/(app)/+layout.svelte] — deferred, pre-existing architecture choice; client-side redirect via $effect is the current pattern
