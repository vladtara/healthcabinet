# Story 15.2: Document Intelligence and Year Confirmation Contract

Status: done

## Story

As a user uploading health documents,
I want the system to persist whether a file is a true analysis and whether its result date needs year confirmation,
So that the app can distinguish lab analyses from plain documents and guide me to resolve incomplete dates instead of silently degrading my dashboard timeline.

## Acceptance Criteria

1. **Persist document intelligence metadata** — The `documents` domain persists:
   - `document_kind: "analysis" | "document" | "unknown"`
   - `needs_date_confirmation: boolean`
   - `partial_measured_at_text: string | null`
   These fields are exposed on both list and detail document API responses.

2. **Deterministic classification rules** — The processing pipeline assigns `document_kind` using persisted output, not UI heuristics:
   - `analysis` when normalized lab values are extracted and persisted
   - `document` when processing succeeds but yields no usable lab values
   - `unknown` only when processing fails or the document is unreadable
   Classification must be stable across reprocessing and reupload.

3. **Yearless-date extraction does not fabricate timestamps** — If the extractor can identify a day/month result date but no year:
   - `measured_at` remains `null` throughout extraction and persistence
   - the extracted partial text is stored in `partial_measured_at_text`
   - `needs_date_confirmation` is set to `true`
   - the document remains actionable and must not be silently treated as a fully resolved completed analysis

4. **Terminal status reflects unresolved year confirmation** — A document with extracted health values and `needs_date_confirmation=true` is stored with `document_kind="analysis"` and terminal document status `partial` unless another existing rule already requires `partial`. Non-analysis documents with no extracted values may still complete successfully as `document_kind="document"` when processing itself succeeds.

5. **Year confirmation endpoint** — Add `POST /api/v1/documents/{id}/confirm-date-year` with body `{ "year": number }`. For an owned document with `needs_date_confirmation=true`, the endpoint:
   - validates the year against the stored `partial_measured_at_text`
   - composes the final `measured_at`
   - updates all `health_values.measured_at` rows for that document
   - clears `needs_date_confirmation`
   - clears `partial_measured_at_text`
   - recalculates terminal document status based on remaining partial conditions
   - invalidates and regenerates the document-scoped AI interpretation

6. **Legacy data migration/backfill** — Add an Alembic migration for the new document columns. Backfill existing documents conservatively:
   - documents with persisted health values => `document_kind="analysis"`
   - documents without persisted health values and status in `completed|partial` => `document_kind="document"`
   - documents with status `failed` => `document_kind="unknown"`
   - legacy rows default `needs_date_confirmation=false` and `partial_measured_at_text=null`
   The migration must not attempt to infer missing-year metadata for old documents.

7. **Minimal frontend contract alignment** — Update frontend API types/helpers so the repo contract matches the backend surface:
   - `Document` and `DocumentDetail` include the new metadata
   - add a typed documents API helper for `confirm-date-year`
   No new UI is required in this story.

8. **Automated coverage** — Backend tests cover classification, yearless-date persistence, year confirmation, measured-at propagation, and AI regeneration behavior. Any touched frontend contract files compile and their unit tests continue to pass.

## Tasks / Subtasks

- [x] Task 1: Extend document persistence model and schemas (AC: 1, 6)
  - [x] Add `document_kind`, `needs_date_confirmation`, and `partial_measured_at_text` to `healthcabinet/backend/app/documents/models.py`.
  - [x] Update `healthcabinet/backend/app/documents/schemas.py` so `DocumentResponse` and `DocumentDetailResponse` expose the new fields.
  - [x] Add an Alembic migration after `015_users_tokens_invalid_before.py` for the new document columns and backfill rules.

- [x] Task 2: Extend extraction and processing state for partial dates (AC: 2, 3)
  - [x] Update `healthcabinet/backend/app/processing/schemas.py` so extraction/graph state can carry both `measured_at` and `partial_measured_at_text`.
  - [x] Update `healthcabinet/backend/app/processing/extractor.py` prompt and validation rules:
    - [x] full date with year => `measured_at` populated, `partial_measured_at_text=null`
    - [x] day/month without year => `measured_at=null`, `partial_measured_at_text` populated
    - [x] no usable date => both null
  - [x] Preserve the existing "JSON only" extractor contract and do not invent a year in the extractor or normalizer.

- [x] Task 3: Persist document intelligence during processing (AC: 2, 3, 4)
  - [x] Add repository helpers in `healthcabinet/backend/app/documents/repository.py` to update document intelligence metadata independently of upload metadata.
  - [x] Update processing orchestration so classification happens from persisted normalized values and extraction metadata, not from frontend assumptions.
  - [x] Update `healthcabinet/backend/app/processing/nodes/finalize_document.py` so terminal status resolves to:
    - [x] `partial` when low-confidence values exist
    - [x] `partial` when `needs_date_confirmation=true`
    - [x] `completed` for analyses with no remaining partial conditions
    - [x] `completed` for successfully processed non-analysis documents
    - [x] `failed` only for unreadable/failed cases

- [x] Task 4: Add year-confirmation service flow (AC: 5)
  - [x] Add a request schema for `{ year: number }` in `healthcabinet/backend/app/documents/schemas.py`.
  - [x] Add `POST /api/v1/documents/{document_id}/confirm-date-year` in `healthcabinet/backend/app/documents/router.py`.
  - [x] Implement service orchestration in `healthcabinet/backend/app/documents/service.py`:
    - [x] enforce ownership via authenticated user
    - [x] reject documents that do not require confirmation
    - [x] compose a timezone-aware final timestamp from `partial_measured_at_text` and the confirmed year
    - [x] update document metadata and all related health values
    - [x] recalculate terminal status after confirmation
    - [x] invalidate and regenerate AI interpretation using existing AI service/repository primitives
  - [x] Return the updated document contract after confirmation.

- [x] Task 5: Add health-value and AI repository helpers for confirmation flow (AC: 5)
  - [x] Add a repository helper in `healthcabinet/backend/app/health_data/repository.py` to bulk-update `measured_at` for all values belonging to a document.
  - [x] Add any mapping helper needed to turn persisted health values back into `NormalizedHealthValue` inputs for `generate_interpretation()`.
  - [x] Reuse `app.ai.repository.invalidate_interpretation()` and `app.ai.service.generate_interpretation()` rather than inventing a second AI persistence path.

- [x] Task 6: Align frontend API contract only (AC: 7)
  - [x] Update `healthcabinet/frontend/src/lib/types/api.ts` to include the new document fields.
  - [x] Add a typed `confirmDateYear(documentId, year)` helper in `healthcabinet/frontend/src/lib/api/documents.ts`.
  - [x] Do not add UI behavior in this story; Story 15.3 and later stories consume the contract.

- [x] Task 7: Backend and contract tests (AC: 8)
  - [x] Add/extend tests in `healthcabinet/backend/tests/processing/test_worker.py` (or adjacent processing tests) for:
    - [x] `analysis` classification with full date
    - [x] `analysis` classification with yearless date => terminal `partial`
    - [x] `document` classification when processing succeeds with no usable lab values
    - [x] `unknown` classification for unreadable/failed cases
  - [x] Add document router/service tests in `healthcabinet/backend/tests/documents/test_router.py` for:
    - [x] new metadata on list/detail responses
    - [x] `confirm-date-year` happy path
    - [x] ownership rejection / missing-confirmation rejection
    - [x] invalid year rejection
  - [x] Add AI-focused tests in `healthcabinet/backend/tests/ai/test_router.py` or service/repository tests to prove interpretation is invalidated/regenerated after confirmation.
  - [x] Run the smallest relevant frontend type/API tests for touched contract files.

## Dev Notes

### Story Scope and Boundaries

- This is a backend-first contract story. It creates the persisted truth that later dashboard, upload, and localization stories build on.
- Do not implement dashboard filtering, dashboard-scoped AI endpoints, multi-upload UI, or the year-confirmation UI surface here. Those belong to Stories `15.3`, `15.4`, and `15.6`.
- Do not rewrite the upload API shape. Fresh upload and reupload remain as they are.
- Do not change the document-detail AI endpoints in this story beyond ensuring their data remains correct after year confirmation.

### Current Codebase Reality

- `healthcabinet/backend/app/documents/models.py` currently stores upload metadata and retry metadata only. No document intelligence fields exist yet.
- `healthcabinet/backend/app/documents/schemas.py` exposes only `status`, upload metadata, and related health values. Frontend `Document` / `DocumentDetail` mirror that contract directly in `healthcabinet/frontend/src/lib/types/api.ts`.
- `healthcabinet/backend/app/processing/schemas.py` currently supports only `measured_at: datetime | None`; the extractor cannot represent a partial date without inventing a full timestamp.
- `healthcabinet/backend/app/processing/extractor.py` currently asks Claude for `"measured_at": "ISO-8601 timestamp or null"`, which is insufficient for yearless lab dates.
- `healthcabinet/backend/app/processing/nodes/finalize_document.py` currently determines terminal status using only `normalized_values` presence and `needs_review` counts.
- `healthcabinet/backend/app/ai/service.py` already exposes `generate_interpretation()` and `app.ai.repository.invalidate_interpretation()`, which should be reused for post-confirmation regeneration.

### Implementation Guardrails

- Keep SQLAlchemy 2.0 style (`Mapped[...]`, `mapped_column()` only).
- Keep repository-layer encryption boundaries intact. New document metadata fields are plain structured metadata and do not require encryption.
- User ownership must continue to come from `get_current_user`, never from request bodies.
- Preserve the current upload/reupload status model: `pending | processing | completed | partial | failed`.
- Do not broaden document-status meaning on the frontend yet. This story makes unresolved year confirmation visible through metadata; UI consumption follows later.

### Classification and Status Rules

- `document_kind` and terminal `status` are related but not identical:
  - an analysis with unresolved year confirmation is `document_kind="analysis"` and `status="partial"`
  - a successful non-analysis document is `document_kind="document"` and can still be `status="completed"`
  - unreadable/failed cases are `document_kind="unknown"` and `status="failed"`
- The classification source of truth must be persisted health values plus extraction metadata, not UI heuristics.
- Avoid recomputing `document_kind` opportunistically in list/detail handlers. Persist once during processing and update intentionally on reprocessing.

### Date Confirmation Rules

- `partial_measured_at_text` stores the extracted source fragment that is missing a year, for example `12.03` or `12 Mar`.
- `measured_at` must remain `null` until the user confirms the year.
- The confirmation path should compose a timezone-aware timestamp at `00:00:00+00:00` for the confirmed day/month/year unless the implementation can preserve a trustworthy extracted time component. The repo currently works with date-only lab results, so UTC midnight is the safest default.
- Confirming the year must update every persisted `health_values.measured_at` row for the document so timeline queries immediately sort correctly.
- After confirmation, clear both `needs_date_confirmation` and `partial_measured_at_text` to prevent repeated prompts.
- After confirmation, recompute terminal document status:
  - if low-confidence values still exist, remain `partial`
  - otherwise transition to `completed`

### Migration and Backfill Rules

- Add a new Alembic revision instead of editing existing migrations.
- Backfill only what can be inferred safely from persisted data.
- Do not attempt to infer missing-year state for legacy rows. The raw extraction fragment is not stored today, so any synthetic backfill would be fiction.
- Prefer explicit server defaults only where they help migration safety; keep runtime defaults aligned with ORM defaults.

### Backend File Targets

- `healthcabinet/backend/app/documents/models.py`
- `healthcabinet/backend/app/documents/schemas.py`
- `healthcabinet/backend/app/documents/router.py`
- `healthcabinet/backend/app/documents/service.py`
- `healthcabinet/backend/app/documents/repository.py`
- `healthcabinet/backend/app/processing/schemas.py`
- `healthcabinet/backend/app/processing/extractor.py`
- `healthcabinet/backend/app/processing/nodes/finalize_document.py`
- `healthcabinet/backend/app/health_data/repository.py`
- `healthcabinet/backend/alembic/versions/016_*.py`

### Frontend Contract Touchpoints

- `healthcabinet/frontend/src/lib/types/api.ts`
- `healthcabinet/frontend/src/lib/api/documents.ts`

No route/component UI work is required here. Keep touched frontend changes contract-only so Story `15.3` can consume the new fields without type drift.

### Testing Requirements

- Start with focused backend tests around the new classification and confirmation rules before wiring broader route coverage.
- Preserve existing tests for upload, document detail, and AI interpretation; update them only where the API response shape legitimately changes.
- For confirmation flow:
  - assert HTTP status first
  - assert document metadata in the response body
  - assert DB state directly for both `documents` and `health_values`
  - assert AI interpretation invalidation/regeneration behavior via repository reads, not only HTTP surface
- Run the smallest relevant frontend tests for touched contract files, then the relevant backend suites.

### Previous Story Intelligence

- Story `2.3` established the current extraction and persistence pipeline, including the existing extractor prompt contract, health-value replacement semantics, and the rule that low-confidence values produce terminal `partial`.
- Story `4.1` and later Epic 4 stories established document-scoped AI interpretation and follow-up chat. Reuse those primitives; do not branch a second document AI storage model.
- Story `14.1` hardened fetch-based SSE auth/lifecycle. Do not change the status event transport in this story.

### Git Intelligence Summary

- Recent commits are concentrated in compliance hardening and cleanup, not in document-processing architecture:
  - `dd88e42 feat(6-3): consent history hardening - /privacy stub route + registration regression + review round 1`
  - `37f3e5e feat(6-2): GDPR account deletion with audit-log erasure marker + review round 2`
  - `29319d0 fix(14-1/14-2): remove duplicate MinIO cleanup, shield anti-pattern, and silent consent API change`
- Inference: keep this story tightly scoped and additive. Avoid broad refactors while the repo is in a stabilization phase.

### Latest Technical Information

- Anthropic official PDF support docs confirm base64 `document` content blocks remain the supported path for PDF understanding in the Messages API, with a 32 MB total request limit and 100-page maximum per request. Keep the existing document-block upload approach in `processing/extractor.py`; this story changes prompt/schema behavior, not transport. Source: https://docs.anthropic.com/en/docs/build-with-claude/pdf-support
- Anthropic official docs also describe PDF processing as combined text-plus-image understanding. That reinforces the need to preserve the original extracted partial date fragment rather than inventing missing structure in downstream code. Source: https://docs.anthropic.com/en/docs/build-with-claude/pdf-support
- No dependency or framework version upgrade is required for this story. Stay on the repo’s current FastAPI, SQLAlchemy, Pydantic, SvelteKit, and Anthropic SDK versions.

### Project Context Reference

- Project rules: `_bmad-output/project-context.md`
- Core planning sources:
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/planning-artifacts/ux-page-specifications.md`
  - `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md`
- Prior implementation context:
  - `_bmad-output/implementation-artifacts/2-3-universal-value-extraction-confidence-scoring.md`
  - `_bmad-output/implementation-artifacts/4-1-plain-language-ai-interpretation-per-upload.md`
  - `_bmad-output/implementation-artifacts/14-1-sse-fetch-based-auth-and-lifecycle.md`

### Completion Status

- Story context created from user scope, sprint plan, project context, architecture, UX specifications, existing processing/AI/document code, recent git history, and current official Anthropic PDF support guidance.
- Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Implementation Plan

1. **Persistence layer (AC 1, 6).** Add three non-null-with-defaults columns to the `documents` ORM (`document_kind` string, `needs_date_confirmation` bool, `partial_measured_at_text` text). Expose all three on `DocumentResponse` and `DocumentDetailResponse`. Author an Alembic revision 016 that ALTERS with server-defaults, backfills from persisted `health_values` membership and existing status, then drops the server-defaults so application-layer ORM defaults become authoritative.
2. **Extraction contract (AC 2, 3).** Add `partial_measured_at_text` to `ExtractionResult` and the graph state dict. Rewrite the Claude system prompt to emit `measured_at` XOR `partial_measured_at_text` XOR both null — with an explicit rule forbidding invented years.
3. **Classification + terminal status (AC 2, 4).** Refactor `finalize_document` so classification, confirmation gating, and terminal status derivation all run off the persisted extraction state. Persist `document_kind` + confirmation metadata alongside the status write in the same session.
4. **Year-confirmation flow (AC 5).** Add a typed `ConfirmDateYearRequest` (with a Pydantic field validator for the hard minimum year), a new router endpoint, two new exception types wired into `main.py`, and a service flow that parses the stored fragment, composes a timezone-aware UTC-midnight timestamp, bulk-updates every `health_values.measured_at` row, clears the flags, recomputes terminal status, then invalidates + regenerates the AI interpretation using the existing primitives.
5. **Frontend contract alignment (AC 7).** Extend `Document` + `DocumentDetail` with the three fields and a `DocumentKind` union, and add `confirmDateYear(...)` to the typed documents client — no UI.
6. **Tests (AC 8).** Focused unit tests on `finalize_document` for the four classification outcomes + the year-confirmation partial rule; extended router tests for metadata presence, happy path, ownership, missing-confirmation, invalid/future year; and an inline AI-regeneration test that asserts invalidate-then-generate ordering via repository reads (not only HTTP surface).

### Completion Notes

- Chose `default="unknown"` for new rows so any row inserted between the migration and the first processing run cannot leak a false positive `analysis` classification.
- Year validation splits cleanly: the Pydantic field validator handles the hard minimum (1900) and produces a 422; the service handles the upper bound (current UTC year) and produces a 400 via `DocumentYearConfirmationInvalidError`. This keeps "request shape is malformed" distinct from "request content is stale/future".
- The confirmation flow commits the measured_at/status/invalidate transaction BEFORE the AI regeneration attempt. A failed regeneration is logged and rolled back locally, but the measured_at resolution stays durable. The AI interpretation is already invalidated, so users never see a stale interpretation on top of a freshly-dated document.
- Timezone: compose at `00:00:00+00:00`. The repo works with date-only lab results today; storing UTC midnight is stable across client locales and lets later timeline queries sort deterministically.
- `partial_measured_at_text` parsing is intentionally conservative — it accepts only the three shapes the extractor is allowed to emit (numeric `dd.mm`/`dd-mm`/`dd/mm`, `dd Mon`, `Mon dd`). Anything else raises `DocumentYearConfirmationInvalidError` so fuzzy client input is never converted into a silently-wrong date.
- Backfill rules for migration are strictly derivable-from-persisted-data. No attempt to infer missing-year state for legacy rows — the source fragment was never stored.
- Extended the existing test_graph.py patch blocks to mock `update_document_intelligence_internal` adjacent to the existing `update_document_status_internal` patches so those tests continue to pass without relaxing their assertions.
- Per orchestration instructions, docker-compose was NOT run in this worktree; the parent agent will run the full backend/frontend suites after merge.

### File List

**Backend code:**
- `healthcabinet/backend/app/documents/models.py` (modified — three new columns)
- `healthcabinet/backend/app/documents/schemas.py` (modified — new DocumentKind literal, fields on DocumentResponse/DocumentDetailResponse, `ConfirmDateYearRequest`)
- `healthcabinet/backend/app/documents/router.py` (modified — `POST /{id}/confirm-date-year`)
- `healthcabinet/backend/app/documents/service.py` (modified — detail response fields; `confirm_date_year()` flow; partial-date parser; records→NormalizedHealthValue mapper)
- `healthcabinet/backend/app/documents/repository.py` (modified — `update_document_intelligence_internal`, `clear_pending_date_confirmation`)
- `healthcabinet/backend/app/documents/exceptions.py` (modified — `DocumentYearConfirmationNotAllowedError`, `DocumentYearConfirmationInvalidError`)
- `healthcabinet/backend/app/processing/schemas.py` (modified — `partial_measured_at_text` on ExtractionResult + DocumentProcessingState + ProcessingGraphState)
- `healthcabinet/backend/app/processing/extractor.py` (modified — system prompt rewrite for day/month-only handling)
- `healthcabinet/backend/app/processing/nodes/extract_values.py` (modified — propagate partial_measured_at_text into graph state)
- `healthcabinet/backend/app/processing/nodes/finalize_document.py` (modified — classification + confirmation-aware status; intelligence write)
- `healthcabinet/backend/app/processing/graph.py` (modified — initialize partial_measured_at_text in graph state)
- `healthcabinet/backend/app/health_data/repository.py` (modified — `update_document_measured_at` bulk helper)
- `healthcabinet/backend/app/main.py` (modified — exception handlers for the two new errors)

**Alembic:**
- `healthcabinet/backend/alembic/versions/016_document_intelligence_fields.py` (new — revision 016, down_revision 015)

**Backend tests:**
- `healthcabinet/backend/tests/processing/test_finalize_document.py` (new — classification + yearless-date rules)
- `healthcabinet/backend/tests/processing/test_graph.py` (modified — added `update_document_intelligence_internal` mock at each finalize_document patch site)
- `healthcabinet/backend/tests/documents/test_router.py` (modified — metadata on list/detail + five confirm-date-year cases + AI invalidate/regenerate ordering)

**Frontend contract:**
- `healthcabinet/frontend/src/lib/types/api.ts` (modified — `DocumentKind` union; `Document` and `DocumentDetail` extended)
- `healthcabinet/frontend/src/lib/api/documents.ts` (modified — `confirmDateYear()` helper)

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-04-19 | dev-agent | Initial implementation of Story 15.2 — document intelligence persistence, yearless-date extraction contract, confirm-date-year endpoint + flow, frontend contract alignment, and backend tests. Alembic revision `016_document_intelligence_fields` added chained from `015`. |

## Review Findings (code review, 2026-04-19)

Four adversarial layers: Blind Hunter, Edge Case Hunter, Acceptance Auditor, QA Agent.

Auditor found a **BLOCKER** in the classification code path that makes AC 2 (the `document` class) and AC 4 ("`completed` for successful non-analysis documents") unreachable at runtime — the associated new unit test was also ticked as complete despite the implementation contradicting it (the full test suite did pass on the 389-test backend run, which is itself a signal that the assertions in `test_finalize_document.py` do NOT actually exercise the dead code path — see QA findings about mocked-out `update_document_intelligence_internal` at the graph level).

### Decision-needed

- [ ] [Review][Decision] **[MEDIUM] Partial-date parser assumes day-first (`dd.mm`) format; US-format `mm.dd` is silently misparsed** [healthcabinet/backend/app/documents/service.py:~398-409] — Extractor preserves the "raw source fragment verbatim". US-printed labs often emit `"3/12"` meaning March 12. Parser treats first numeric group as day → composes Dec 3 instead. Options: (a) accept this — all HealthCabinet users are in EU-format locales; (b) constrain extractor prompt to ALWAYS reorder to `dd.mm` canonical (losing audit-trail fidelity); (c) persist a format hint alongside the raw fragment; (d) return 409 on ambiguous shapes and surface a "confirm both year AND date" UI (Story 15.6 territory). Needs product decision.
- [ ] [Review][Decision] **[MEDIUM] AI regeneration failure in `confirm_date_year` returns 200 OK with no user-visible signal** [healthcabinet/backend/app/documents/service.py:~582-599] — Spec Completion Notes explicitly documents this as "best effort — year resolution stays durable". But the UI has no way to know regeneration failed. Options: (a) accept — interpretation will refresh on next document detail view by some other mechanism; (b) add a response flag (`ai_regeneration_failed: boolean`) + a retry endpoint; (c) enqueue a worker retry. Needs product decision on how observable this failure should be.

### Patch (unambiguous fix)

- [ ] [Review][Patch] **[HIGH] `document_kind="document"` classification is UNREACHABLE at runtime — AC 2 and AC 4 both violated** [healthcabinet/backend/app/processing/nodes/finalize_document.py:88,91] — `fallback.error_stage = "finalize_document"` is set at line 88 BEFORE `_resolve_document_kind(state, fallback)` runs at line 91. `_resolve_document_kind` returns `"document"` only if `fallback.error_stage is None` (line 36), so that branch is dead. A successful extraction with zero lab values classifies as `"unknown"` and `_resolve_terminal_outcome` falls through to `return "failed"` (line 79). Result: non-analysis documents (consent forms, referrals, unreadable-but-not-failing prints) terminate with status=`failed` and document_kind=`unknown` instead of the spec'd status=`completed` + document_kind=`document`. Fix: snapshot `fallback.error_stage` BEFORE stamping the finalize name, and pass the snapshot into `_resolve_document_kind`, OR move the stamp to after classification.
- [ ] [Review][Patch] **[HIGH] The "no lab values → document" unit test is asserting against dead code and will fail when the bug is fixed (or vice versa)** [healthcabinet/backend/tests/processing/test_finalize_document.py:~163-189] — The test sets `fallback.error_stage = None` and asserts `document_kind == "document"` + terminal_status `== "completed"`. Against the current implementation (with the bug), this test cannot pass the real code path — it passes only because it patches `update_document_intelligence_internal` and `update_document_status_internal` as `AsyncMock()` with no call-count assertions, silently swallowing the mismatch. Confirm the test is genuinely exercising the path after the fix above. Also: existing graph test `test_run_processing_graph_failed_path_with_no_usable_values_and_no_prior_values` in `test_graph.py:~297` asserts terminal_status `== "failed"` for the same case — this must flip to `"completed"` after the fix.
- [ ] [Review][Patch] **[MEDIUM] Migration 016 backfill order can overwrite `analysis` with `unknown` for `status='failed'` rows that still have persisted health values** [healthcabinet/backend/alembic/versions/016_document_intelligence_fields.py:~92-109] — AC 6 lists "documents with persisted health values ⇒ analysis" first, "documents with status `failed` ⇒ unknown" third. The third UPDATE scopes on status=failed UNCONDITIONALLY — a legacy row that failed after persisting values is classified `unknown`, hiding the real persisted analysis. Fix: add `AND id NOT IN (SELECT DISTINCT document_id FROM health_values)` to the third UPDATE.
- [ ] [Review][Patch] **[MEDIUM] `invalidate_interpretation` is committed before regeneration is guarded by `if values_for_ai`; an empty `values_for_ai` set leaves the interpretation permanently invalidated with no regeneration path** [healthcabinet/backend/app/documents/service.py:~587-601] — Narrow failure mode (confirm-date-year requires `needs_date_confirmation=true` which implies ≥1 value), but a concurrent reprocess that wipes rows between read and regen reopens the window. Fix: either gate the invalidation on `len(values_for_ai) > 0`, or short-circuit the entire endpoint earlier if no persisted values remain.
- [ ] [Review][Patch] **[MEDIUM] `update_document_measured_at` blindly overwrites rows with existing `measured_at`** [healthcabinet/backend/app/health_data/repository.py:~619-644] — `UPDATE health_values SET measured_at = :ts WHERE document_id = :doc AND user_id = :user` with no `AND measured_at IS NULL` guard. If a document mixed full-date rows with yearless rows (schema allows), confirming the year clobbers correct timestamps. Defense: add the null-guard; document the invariant that measured_at is per-document, not per-row, if that's intended.
- [ ] [Review][Patch] **[MEDIUM] `update_document_intelligence_internal` has no ownership check, inconsistent with sibling helpers** [healthcabinet/backend/app/documents/repository.py:~184-211] — Sibling helpers (`update_document_measured_at`, `clear_pending_date_confirmation`) scope by `user_id` for defense-in-depth. This one filters only on `Document.id`. Docstring says "ownership enforced upstream by queue dispatcher" — fine, but a future non-pipeline caller has no safety net. Fix: accept `user_id: UUID | None = None` and scope when provided; keep the pipeline call site unchanged.
- [ ] [Review][Patch] **[MEDIUM] Hyphen-separated named-month fragments (`"12-Mar"`) fail the parser and permanently jam the document** [healthcabinet/backend/app/documents/service.py:~408-415] — Common on European printed labs. Patterns 2/3 require whitespace between numeric and named parts. The user is stuck — no API to edit `partial_measured_at_text` and no alternative recovery path. Fix: expand pattern 2 to accept `[\s\-\.]+` between day and month.
- [ ] [Review][Patch] **[MEDIUM] `ConfirmDateYearRequest` accepts floats and coerces (`year=2026.9 → 2026`)** [healthcabinet/backend/app/documents/schemas.py:~111-122] — Pydantic v2 default is non-strict. Add `Field(strict=True)` or a validator that rejects non-integer input as 422.

### Patch (test coverage gaps)

- [ ] [Review][Patch] **[HIGH] No test exercises the Alembic 016 migration itself** — Test fixture uses `Base.metadata.create_all`, bypassing migrations. Add an integration test that runs `alembic upgrade 015 → 016` with seeded rows per backfill category, asserts classification, then runs `downgrade 015` and asserts column removal.
- [ ] [Review][Patch] **[HIGH] Happy-path test uses single health_value row — bulk `measured_at` propagation is unverified** [healthcabinet/backend/tests/documents/test_router.py:~963-1024] — AC 5 explicitly requires "updates ALL `health_values.measured_at` rows for that document". A typo'd `WHERE` clause passes. Seed ≥3 rows (some with pre-set measured_at, some null), confirm, and assert ALL were updated to the resolved UTC midnight.
- [ ] [Review][Patch] **[HIGH] Happy-path assertions only read HTTP response, not DB state (contradicts the spec's explicit testing rule)** [healthcabinet/backend/tests/documents/test_router.py:~1014-1024] — Dev Notes line 197: "assert DB state directly for both `documents` and `health_values`". Currently reads only the response body. Add direct SQLAlchemy queries post-call.
- [ ] [Review][Patch] **[HIGH] AI regeneration failure path has zero tests** [healthcabinet/backend/app/documents/service.py:~582-599] — Patch `generate_interpretation` to raise; assert 200 response, `measured_at` + `needs_date_confirmation=False` persisted, and the interpretation stays invalidated. Prevents regression where exception re-raises or commit-ordering loses the year confirmation.
- [ ] [Review][Patch] **[HIGH] `_parse_partial_date` tested only with `"12.03"`; `dd/mm`, `dd-mm`, `"12 Mar"`, `"Mar 12"`, Feb 30, junk strings, Feb 29 non-leap — all untested** — Add a parametrized unit test over ~10 canonical shapes, asserting `DocumentYearConfirmationInvalidError` for invalid shapes.
- [ ] [Review][Patch] **[HIGH] Frontend `confirmDateYear` helper + new `Document`/`DocumentDetail` fields are untested** [healthcabinet/frontend/src/lib/api/documents.ts, types/api.ts] — Task 7 subtask "Run the smallest relevant frontend type/API tests". Add a vitest case mocking `apiFetch` and asserting URL + POST + body, plus a compile-time type guard test.
- [ ] [Review][Patch] **[MEDIUM] Graph-level tests `new=AsyncMock()` the intelligence-update call with no post-assertion** [healthcabinet/backend/tests/processing/test_graph.py:~118-120,205-207,271-273,339-341,548-550,694-696] — No assertion that the call happens at all, let alone with correct kwargs. In at least one happy-path graph test, replace `AsyncMock()` with a recording helper and assert `call_args == {document_kind: "analysis", ...}`.
- [ ] [Review][Patch] **[MEDIUM] No test for reprocessing a previously-classified document — classification must recompute** — Run `finalize_document` twice with different states (analysis-with-date, then document-with-no-values), assert two distinct `update_document_intelligence_internal` calls.
- [ ] [Review][Patch] **[MEDIUM] Boundary year coverage missing: `year==1900` (inclusive min) + `year==current_year` (dynamic upper bound)** — Add parametrized tests including `(1900, current_year-1, current_year)` passing and `(1899, current_year+1)` failing. Freeze time to avoid calendar flakiness.
- [ ] [Review][Patch] **[MEDIUM] Defensive `if not doc.partial_measured_at_text` branch in service is untested** [healthcabinet/backend/app/documents/service.py:~529-535] — Add a test with `needs_date_confirmation=True` + `partial_measured_at_text=None` asserting 400.
- [ ] [Review][Patch] **[MEDIUM] Extractor prompt contract change is not tested** — No test asserts the extractor correctly returns `{measured_at: null, partial_measured_at_text: "12.03"}` for a yearless input, or that a legacy response missing the new field still parses.
- [ ] [Review][Patch] **[MEDIUM] `update_document_measured_at` repository helper has no direct unit test** [healthcabinet/backend/tests/health_data/test_repository.py] — Ownership filter regression could silently match zero rows. Add a repository-level test with user A and user B data, assert rowcount + user B's rows untouched.
- [ ] [Review][Patch] **[MEDIUM] AI regeneration test calls a fake that bypasses the real service's safety-validation** [healthcabinet/backend/tests/documents/test_router.py:~1123-1221] — The real `generate_interpretation` has a safety gate. A regression that skips it post-confirmation won't be caught. Either assert the real service is called, or add a second test that lets the real service run with a mocked LLM client.
- [ ] [Review][Patch] **[MEDIUM] Timezone handling not asserted — test uses `startswith("2026-03-12")`** [healthcabinet/backend/tests/documents/test_router.py:~1022] — Dev Notes require `00:00:00+00:00`. A regression to naive datetime would ship green. Assert the full ISO string or parse and check `tzinfo == UTC`.

### Defer (pre-existing / environment)

- [x] [Review][Defer] **[MEDIUM] Migration lock duration on very large documents table (Postgres ACCESS EXCLUSIVE for the entire backfill)** [healthcabinet/backend/alembic/versions/016_document_intelligence_fields.py] — deferred; acceptable for current database size. Revisit when rolling out to prod with >1M documents. Listed in deferred-work.md.
- [x] [Review][Defer] **[LOW] Test fixture isolation risk — confirmation tests commit rows that the session fixture's rollback may or may not clean depending on driver semantics** — deferred; related to the broader flaky fixture ordering hint we already saw on first-run backend tests.
- [x] [Review][Defer] **[LOW] Retry-failure path does not clear stale `partial_measured_at_text`** — deferred, narrow edge case (retry aborts before finalize_document but after prior partial was persisted).
- [x] [Review][Defer] **[LOW] Two concurrent `confirm_date_year` requests for the same document race on the AI memory UNIQUE constraint** — deferred; narrow failure mode, no data corruption risk — just an ai_regeneration_failed log on the loser.
- [x] [Review][Defer] **[LOW] Extractor state serialization compatibility between old and new `partial_measured_at_text` field** — deferred, no evidence this is broken.
- [x] [Review][Defer] **[LOW] `DocumentKind` Literal response-time validation of a bad DB value** — deferred; admin hardening belongs to 15.3.

### Dismissed as noise (5)

Stylistic comments on dead `ValueError` branches in regex-captured code; request for a "confirmation success" flag that's outside AC scope; concurrent-delete-of-all-rows-between-update-and-read window (hypothetical, no real trigger); UTC-year edge for timezones >UTC+0 on Dec 31/Jan 1 (tolerable); `year >= current_year + 1` slack (judgment call).

## Review Findings (code review round 2, 2026-04-19)

Round 2 reviewed ONLY the Round 1 patch commits (`6c1b5e8` + `0bbb631`). Four layers ran. Auditor declared **`ROUND 2 CLEAN`** on the BLOCKER fix and all 8 Acceptance Criteria. Other layers flagged secondary issues worth addressing before final sign-off.

### Patch (HIGH — potential correctness hazards from Round 1 patches)

- [ ] [Review][Patch] **[HIGH] `invalidate_interpretation` gate may leave stale interpretation valid on concurrent reprocess** [healthcabinet/backend/app/documents/service.py:593-597] — Round 1 Fix H gated `invalidate_interpretation` on `values_for_ai` being non-empty, to avoid a permanent-invalidation-with-no-retry-path edge. But the gate INVERTS the safety contract: if a concurrent reprocess wipes rows between `list_values_by_document` and the regen, OR if all rows fail decryption (records empty + skipped_corrupt_records>0), the user-confirmed year is committed but the prior interpretation stays `safety_validated=True` — even though it describes measurements at an unresolved date. Users see a "valid" interpretation that contradicts the newly-confirmed year. Fix: always call `invalidate_interpretation` (cheap, idempotent); only gate the `generate_interpretation` regeneration on `values_for_ai`. The "no retry path" concern is moot — if no values, nothing to regenerate, and the interpretation SHOULD be invalid until new values land via re-upload.
- [ ] [Review][Patch] **[HIGH] `_bind_node` unconditional `error_stage`/`error_message` clear on success can erase legitimate diagnostic breadcrumbs** [healthcabinet/backend/app/processing/graph.py:47-57] — The wrapper clears both fields after ANY successful node return. Today no node uses that pattern, but the follow-up commit message explicitly admits the assumption "nodes only stamp on entry; a node that sets `error_message` for soft-failure logging and returns normally would have its breadcrumb silently wiped." Soft-failure nodes (e.g. a future "best-effort AI regen" pattern) would lose their signal. Fix: clear only if the current stage matches the node's own name (`if fallback_state.error_stage == node.__name__: fallback_state.error_stage = None`), preserving any state a node deliberately set for downstream consumers.

### Patch (MEDIUM)

- [ ] [Review][Patch] **[MEDIUM] `update_document_intelligence_internal` `user_id=None` default is dangerously opt-in defense** [healthcabinet/backend/app/documents/repository.py:~184-211] — Round 1 Fix I made the param optional with `user_id=None` defaulting to "no ownership filter". A future caller forgetting to thread `user_id` gets silent cross-user writes. Fix: make `user_id` required (no default); pipeline caller in `finalize_document.py` passes `user_id=None` explicitly with an inline comment justifying the unscoped write. Or split into `_unsafe` (pipeline-only) and `_safe` (user-scoped) variants.
- [ ] [Review][Patch] **[MEDIUM] Unicode dashes break partial-date parser post-Fix-J** [healthcabinet/backend/app/documents/service.py:~409-419] — Fix J expanded the separator class to `[\s\-\.]+` but only ASCII hyphen. En-dash (U+2013), em-dash (U+2014), and minus-sign (U+2212) are common in copy-paste from typeset PDFs (e.g. `"12–Mar"`). Such fragments fall through all three patterns, return None, and the confirmation endpoint responds 400 with no recovery path. Fix: expand the regex to include Unicode dash variants, OR normalize the fragment (`partial_measured_at_text.translate(...)`) before matching.
- [ ] [Review][Patch] **[MEDIUM] TH happy-path test no longer covers "overwrites pre-populated measured_at"** [healthcabinet/backend/tests/documents/test_router.py:~905-991] — The Round 1.5 followup (commit `0bbb631`) deleted the `HealthValue.__table__.update()` stanza that pre-seeded one row with a stale `measured_at` timestamp. All three rows now start at `measured_at=None`. AC 5 requires "updates ALL rows regardless of prior state"; a regression adding `AND measured_at IS NULL` to `update_document_measured_at` would pass this test. `test_update_document_measured_at_is_user_scoped` also only seeds null rows. Fix: add a dedicated repo-level test that seeds a row with a stale non-null `measured_at` and asserts overwrite. Use ORM attribute assignment (not Core UPDATE) to avoid the identity-map drift that caused the Round 1.5 issue.
- [ ] [Review][Patch] **[MEDIUM] TG graph-level analysis test skips `partial_measured_at_text is None` assertion** [healthcabinet/backend/tests/processing/test_graph.py:~163-166] — Symmetrical with the new `completes_as_document` test. If the finalizer's `partial_text = state[...] if needs_date_confirmation else None` gate regressed (yearless text bleeding into fully-dated analyses), only the document test would catch it. Add the assertion for symmetry.
- [ ] [Review][Patch] **[MEDIUM] Fixture isolation: confirm-date-year tests commit rows that the session fixture's `rollback()` can't clean** [healthcabinet/backend/tests/conftest.py:48-54 + test_router.py TH/TI/TJ] — New tests in this set are the first in the suite that commit via the service layer. Unique per-test emails prevent immediate clash, but rows accumulate indefinitely (documents, users, health_values, ai_memory). Upgrades Round 1's LOW defer to MEDIUM because this is the first batch of committing tests. Fix: wrap `async_db_session` in a SAVEPOINT pattern (`begin_nested()` with listener restart), OR add explicit per-test cleanup of rows by user_id.
- [ ] [Review][Patch] **[MEDIUM] TJ boundary year test is calendar-flaky** [healthcabinet/backend/tests/documents/test_router.py:~1399-1460] — Test reads `current_year = datetime.now(UTC).year` once at top, then service recomputes at call time. On Dec 31 → Jan 1 UTC boundary, `current_year+1 → 400` flips to `2027 → 200`. Round 1 suggestion to freeze time was not implemented. Fix: `freezegun` or `patch("app.documents.service.datetime")` to pin the anchor for the test's duration.

### Defer (carryover from Round 1 + low-priority)

- [x] [Review][Defer] **[LOW] `update_document_measured_at` still has no `measured_at IS NULL` guard** — Round 1 MEDIUM [Patch] item. TH workaround (remove pre-seed) sidesteps rather than resolves. Low today because `replace_document_health_values` delete-and-reinsert makes mixed rows unreachable.
- [x] [Review][Defer] **[LOW] Extractor prompt contract change remains untested** — Round 1 MEDIUM [Patch] item, not addressed in Round 2. Would catch regression where Claude emits legacy-shaped JSON.
- [x] [Review][Defer] **[LOW] Alembic 016 migration still unexercised by tests** — Round 1 HIGH [Patch] item. Conftest uses `Base.metadata.create_all` so the backfill is purely unit-logic-reviewed. Lower risk now that Fix G's `NOT IN` backfill exclusion is in place, but still a known gap.
- [x] [Review][Defer] **[LOW] AI safety-validator regression still uncatchable by tests** — Round 1 MEDIUM [Patch] item. Happy-path + regen-failure tests patch `generate_interpretation` at the service entry, bypassing the real safety gate.
- [x] [Review][Defer] **[LOW] TP parser test doesn't cover `Mar.12` / `12.Mar` / trailing-dot variants** — Fix J expanded the class, no test pins each separator variant.
- [x] [Review][Defer] **[LOW] Widened `[\s\-\.]+` regex accepts doubled/spaced separators (`"12--Mar"`, `"12 - - Mar"`)** — Lenient but not wrong; could mask upstream extractor regressions.
- [x] [Review][Defer] **[LOW] ConfirmDateYearRequest strict=True docstring contradicts the docstring comment** — Docstring says "transport-layer stays plain int to avoid conflation"; Fix K adds strict=True which IS transport validation.
- [x] [Review][Defer] **[LOW] Migration `NOT IN` subquery footgun if `health_values.document_id` ever becomes nullable** — Prefer `NOT EXISTS`. Not nullable today.
- [x] [Review][Defer] **[LOW] `doc_id_uuid = doc.id` caching is defensive but unnecessary (PKs don't lazy-load)** — Commit message root-cause narrative was slightly inaccurate but the fix works.

### Dismissed as noise (4)

`ProcessingGraphFallbackState` reuse-across-runs scenario (not architecturally reachable); TA test call-count semantics (kwargs assertions are sufficient); parser whitespace-trimming coverage (already covered by anchors); TFE `toMatchObject` vs strict equality (tight enough for the test's purpose).
