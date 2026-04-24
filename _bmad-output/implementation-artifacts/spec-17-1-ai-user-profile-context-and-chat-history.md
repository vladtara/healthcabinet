---
title: 'AI user profile context + persistent chat history (v1)'
type: 'feature'
created: '2026-04-24'
status: 'approved'
baseline_commit: 'ff0f4a7b1725e5bad2cc9b934563699464223b14'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The AI assistant has two gaps surfaced after the filter-caching work:

1. **No user profile in AI context.** The assistant doesn't know the user's age, sex, known conditions, current medications, or family history. Clinical reasoning over labs without that baseline is shallow — "TSH borderline high" means something different for a 28-year-old woman on levothyroxine than for a 62-year-old man with no meds. A `UserProfile` table already exists (`backend/app/auth/models.py:38-65`) and a Settings page already ships, but profile fields are (a) stored plaintext despite being PHI and (b) never injected into chat prompts.
2. **Chat is stateless.** Both document-scoped (`POST /api/v1/ai/chat`) and dashboard-scoped (`POST /api/v1/ai/dashboard/chat`) endpoints keep messages only in the browser tab. Reload or navigation wipes the conversation; the model cannot reference prior turns.

**Approach (v1):**

1. Encrypt existing `UserProfile` PHI columns at rest via a **two-phase migration** (add encrypted columns + dual-write → drop plaintext in a follow-up deploy). Array fields serialized-then-encrypted as one blob per field, not per-element (avoids cardinality leaks via GCM).
2. Build a `[User profile]` system-prompt block and inject it into both chat prompt builders. Canonical data — never routed through any memory tool.
3. Persist chat messages in a new **single-source-of-truth** audit table `ai_chat_messages` (encrypted `text` column). No LangGraph checkpointer in v1 — the checkpointer adds complexity without fixing the UI-pagination requirement.
4. Derive `thread_id` **server-side only**: `doc:{user_id}:{document_id}` for per-document chat, `dash:{user_id}:{document_kind}` for dashboard chat. Filter change on the dashboard = hard thread reset with a UI toast ("Started a new conversation for this filter") — continuing the same thread across filter switches produces contradictory reasoning.
5. Frontend chat components hydrate from the audit table on mount and invalidate the query on stream completion; no optimistic writes.
6. Prompt cache breakpoint placed after the stable block `[profile] → [main summary] → [filter view] → [prior docs]` and before the volatile `[recent messages] → [user question]`.

**Explicit v2 follow-ups (out of scope for this spec):**

- Anthropic `memory_20250818` tool integration + `chat_memories` table for cross-thread semantic memory.
- LangGraph `AsyncPostgresSaver` checkpointer for resumable graph state.
- Distilled rolling summary of older turns (when prompt budget starts to bite).

## Boundaries & Constraints

**Always:**
- Profile fields stored encrypted at rest via `app.core.encryption.encrypt_bytes/decrypt_bytes` (AES-256-GCM). `height_cm` and `weight_kg` stay plaintext (not PHI in isolation; handy for future BMI computations in SQL).
- `thread_id` is derived server-side from `(user_id, document_id)` or `(user_id, document_kind)`. The client never sends it; never returned in URLs.
- Audit row for the user message is persisted **before** streaming begins. The assistant row is persisted **only on successful stream completion** — stream cancellation / safety block leaves no half-turn in the audit log.
- Profile block is only injected into chat prompts (`stream_follow_up_answer`, `stream_dashboard_follow_up`). It must **not** be added to `generate_dashboard_interpretation` / `_generate_and_persist_overall` — those are deterministic aggregate notes.
- Existing `GET/PUT /api/v1/users/me/profile` request/response schemas stay wire-compatible (`ProfileResponse`, `ProfileUpdateRequest`). External contract unchanged.

**Ask First:**
- If the existing settings page has form validation that would surface differently under encrypted storage (e.g., server-side range check that previously returned the value back), confirm the replay shape before patching tests.
- If the production DB has >100k `user_profiles` rows, switch the phase-1 backfill from a single transaction to batches of 1000 with savepoint per batch.

**Never:**
- Do not drop the plaintext `age`, `sex`, `known_conditions`, `medications`, `family_history` columns in phase-1. They are dropped in a separate phase-2 migration (subsequent deploy) after dual-write has been verified live.
- Do not introduce the Anthropic memory tool or a `chat_memories` table in this change — deferred to v2.
- Do not introduce a LangGraph `AsyncPostgresSaver` — deferred to v2.
- Do not accept `thread_id` from the client or expose it in URLs / response bodies.
- Do not persist an assistant chat row when the stream was aborted or safety-truncated.
- Do not change the rate limiting, safety-pattern list, or disclaimer strings in `safety.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Behavior | Error Handling |
|----------|--------------|-------------------|----------------|
| Empty profile | User never saved settings | `_build_profile_block` returns `None`; no `[User profile]` block emitted; prompt shorter | — |
| Partial profile | Only age + sex filled | Block renders the two filled lines, omits others | — |
| Array field set | `known_conditions=["hypothyroidism","migraine"]` | Rendered as `Conditions: hypothyroidism, migraine` | — |
| Profile update | User edits Settings, saves | Next chat turn reads the new values (no cache) | 4xx on validation errors; RFC 7807 response |
| First chat turn | No prior messages in thread | Rehydration returns empty list; prompt has no `[Recent conversation]` block | — |
| Multi-turn chat | 5 prior turns in thread | `list_chat_messages(limit=20)` returns oldest→newest; injected under `[Recent conversation]` | — |
| Page reload | Mid-conversation, user reloads | Chat window re-hydrates from audit table; prior turns visible | TanStack Query `staleTime` per existing pattern |
| Filter switch (dashboard) | User on `all`, switches to `analysis` | Dashboard chat thread id flips; different message list loaded; toast shown: "Started a new conversation for this filter" | — |
| Stream cancellation | User navigates away mid-stream | User row persisted; assistant row **not** persisted; next hydration shows only the user turn | Close handled in streaming handler |
| Safety-blocked reply | Safety pipeline truncates the stream | User row persisted; assistant row **not** persisted (truncated fallback is emitted as a chunk but not stored) | — |
| Clear conversation | User clicks "Clear" | `DELETE /api/v1/ai/chat/{doc}/messages` removes only that thread's rows | 404 if document not owned by user |
| Thread isolation | User A forges a document_id owned by B | `GET /api/v1/ai/chat/{B-doc}/messages` auth'd as A returns 404 via ownership check | — |
| Migration rollback | Phase-1 applied, app redeployed with older code | Plaintext columns still present; app reads them; encrypted columns ignored | Phase-1 is reversible until phase-2 drops plaintext |
| Encryption key missing | `ENCRYPTION_KEY` unset on app boot | Startup fails loudly (existing behavior for `ai_memories`) | — |

</frozen-after-approval>

## Code Map

**Backend — data layer:**
- `healthcabinet/backend/app/auth/models.py:38-65` — `UserProfile`; add `age_encrypted`, `sex_encrypted`, `known_conditions_encrypted`, `medications_encrypted`, `family_history_encrypted` columns (`LargeBinary`, nullable). Plaintext columns kept in v1 (dropped in phase-2).
- `healthcabinet/backend/app/core/encryption.py` — reuse `encrypt_bytes` / `decrypt_bytes` primitives (AES-256-GCM; already powering `ai_memories.interpretation_encrypted`).
- `healthcabinet/backend/alembic/versions/0XX_user_profile_encryption_phase1.py` (new) — adds encrypted columns, backfills in Python using `encrypt_bytes`, adds `CHECK (octet_length(...) BETWEEN 28 AND 64 OR ... IS NULL)` to catch accidental plaintext inserts.
- `healthcabinet/backend/alembic/versions/0XY_ai_chat_messages.py` (new) — creates `ai_chat_messages` table (id UUID PK, user_id FK cascade, thread_id TEXT, role TEXT CHECK IN ('user','assistant'), text_encrypted BYTEA, created_at TIMESTAMPTZ); index on `(user_id, thread_id, created_at)`.

**Backend — repositories:**
- `healthcabinet/backend/app/users/repository.py` (extend or create) — `get_decrypted_profile(db, user_id)`, `upsert_profile(db, user_id, fields)`; helpers `_encrypt_json_list`, `_decrypt_json_list`.
- `healthcabinet/backend/app/ai/repository.py` — add `append_chat_message(db, user_id, thread_id, role, text)`, `list_chat_messages(db, user_id, thread_id, limit, before)`, `count_chat_messages(db, user_id, thread_id)`, `clear_thread(db, user_id, thread_id)`.

**Backend — service / prompt assembly:**
- `healthcabinet/backend/app/ai/service.py::_build_profile_block` (new) — renders lines (`Age:`, `Sex:`, `Conditions:`, `Medications:`, `Family history:`); omits missing fields; returns `None` when entirely empty.
- `healthcabinet/backend/app/ai/service.py::_build_follow_up_prompt` — extend signature with `profile_block: str | None` and `recent_messages: list[ChatMessageRecord]`; renders them in canonical order before the `[Main health summary]` anchor (profile) / before `[User question]` (recent messages).
- `healthcabinet/backend/app/ai/service.py::_build_dashboard_prompt` — parallel extension.
- `healthcabinet/backend/app/ai/service.py::stream_follow_up_answer` — derive `thread_id = f"doc:{user_id}:{document_id}"`; fetch profile + last 20 messages; persist user row before streaming; persist assistant row on successful completion.
- `healthcabinet/backend/app/ai/service.py::stream_dashboard_follow_up` — parallel for `thread_id = f"dash:{user_id}:{document_kind}"`.

**Backend — router / schemas:**
- `healthcabinet/backend/app/ai/router.py` — add 4 endpoints:
  - `GET /api/v1/ai/chat/{document_id}/messages?limit=50&before=<cursor>`
  - `GET /api/v1/ai/dashboard/chat/messages?document_kind=<kind>&limit=50&before=<cursor>`
  - `DELETE /api/v1/ai/chat/{document_id}/messages`
  - `DELETE /api/v1/ai/dashboard/chat/messages?document_kind=<kind>`
- `healthcabinet/backend/app/ai/schemas.py` — add `ChatMessageResponse`, `ChatMessageListResponse`, `ChatMessageRole` enum.
- `healthcabinet/backend/app/users/service.py` / `users/router.py` — wire `get_profile` / `update_profile` to repository helpers. External contract unchanged.

**Frontend:**
- `healthcabinet/frontend/src/lib/api/ai.ts` — add `listDocumentChatMessages`, `listDashboardChatMessages`, `clearDocumentChat`, `clearDashboardChat`.
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte` — TanStack query `['chat','dash', documentKind]` hydration; toast on filter switch; clear-conversation button.
- `healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte` — parallel hydration scoped to `documentId`.
- `healthcabinet/frontend/src/routes/(app)/settings/+page.svelte` — no functional change; smoke-tested against encrypted backend.

**Tests (all inside Docker per `CLAUDE.md`):**
- `healthcabinet/backend/tests/users/test_profile_encryption.py` (new) — encrypt/decrypt roundtrip, migration backfill, cascade delete.
- `healthcabinet/backend/tests/ai/test_chat_history.py` (new) — persistence, pagination, thread isolation, filter-switch reset, clear-endpoint, no-persist-on-abort.
- `healthcabinet/backend/tests/ai/test_prompt_assembly.py` (new or extend `test_chat_context.py`) — profile block rendering, presence in prompts, recent-messages block, cache-breakpoint ordering.

## v2 follow-up spec (not in this change)

Once this ships and real gaps surface, a successor spec should cover:
- Anthropic `memory_20250818` beta tool integration + `chat_memories` table (encrypted per-user path namespace, 8 KB / 256 KB / 32-file caps, rate limit 10 writes / 5min).
- LangGraph `AsyncPostgresSaver` checkpointer if multi-turn human-in-the-loop branching becomes a requirement.
- Background distillation job: compact older chat messages into a rolling summary memory to stay under prompt budget on long-running threads.

## Verification

1. `docker compose up -d --build backend worker frontend`
2. `docker compose exec backend alembic upgrade head`
3. `docker compose --profile test run --rm backend-test uv run pytest tests/users/test_profile_encryption.py tests/ai/test_chat_history.py tests/ai/test_prompt_assembly.py -v`
4. Regression: `docker compose --profile test run --rm backend-test uv run pytest tests/ai/ tests/users/ tests/documents/ tests/processing/ -q`
5. Lint+types: `docker compose --profile test run --rm backend-test bash -c 'uv run ruff check app/ tests/ && uv run mypy app/'`
6. Manual smoke at `http://localhost:3000`:
   - Settings → fill age, sex, one custom condition, medications, family history → Save.
   - Open a lab document → ask a question that references profile (e.g. "given my hypothyroidism, how should I read this TSH?"). AI references the profile explicitly.
   - Reload the page. Prior Q&A still visible in the chat window.
   - Dashboard → switch filter `all` → `analysis` → observe toast; prior thread not shown. Switch back → prior `all` thread visible again.
   - Inspect `ai_chat_messages` rows in Postgres: `text_encrypted` is bytea (unreadable); roles correct; thread_ids match scheme.

## Risks & mitigations

- **Key rotation.** v1 doesn't change the key model; document in the phase-2 PR that rotation requires re-encrypting `user_profiles` + `ai_memories` + `ai_chat_messages` together.
- **Production DB size.** Phase-1 backfill is one-shot; if profile count exceeds ~100k, switch to batches of 1000 with per-batch savepoint.
- **Partial stream.** Intentional: cancelled/blocked streams don't persist an assistant row. Handler documents this.
- **Empty profile on first use.** Block returns `None`; prompt stays shorter. Tested.
