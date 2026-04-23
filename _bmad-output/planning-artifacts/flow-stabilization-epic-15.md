---
epic: 15
title: Flow Stabilization and Dashboard Intelligence
status: approved
created: 2026-04-18
source:
  - user scope: "Fix Plan: Uploads, EN/UA, Recognition, Dashboard AI, Session, Chat UX"
  - scrum-master sprint plan (2026-04-18)
---

# Epic 15: Flow Stabilization and Dashboard Intelligence

## Outcome

Stabilize the product around document ingestion, dashboard AI, authentication restore, and core UX reliability without rewriting the existing architecture. This epic closes the gap between the shipped MVP surface and the actual expected user flows: multi-file import, reliable session restore, correct document recognition, actionable year confirmation for incomplete analysis dates, dashboard-scoped AI context, and usable long-form AI chat.

## Why This Epic Exists

The current product ships the core primitives, but several high-value flows still behave like stitched-together feature slices instead of one coherent system:

- upload remains single-file even though the product promise is cross-document intelligence
- dashboard AI is still coupled to the latest document instead of the active dashboard dataset
- the app cannot persist document-level intelligence about whether a file is an analysis, a plain document, or unresolved
- yearless laboratory dates silently degrade timeline quality because the system cannot ask the user to resolve the missing year
- session restore races route guards on hard reload
- long AI conversations are hard to use because the chat pane overflow behavior is wrong
- core flows still use hard-coded English strings

## Epic Constraints

- Keep the existing backend upload endpoint shape for batch import in this pass; the batch flow is client-orchestrated over the single-file API.
- Preserve current auth model: access token in memory, refresh token in httpOnly cookie.
- Dashboard AI becomes dashboard-scoped; document detail AI remains document-scoped.
- Reupload remains single-file and must not be merged into the batch UX.
- Desktop-only MVP constraints remain in force.

## Story Sequence

### Story 15.1: Auth Bootstrap Restore Guard

As an authenticated user,
I want route guards to wait until session restoration finishes on page reload,
So that I stay signed in instead of being bounced to login during bootstrap.

Acceptance criteria summary:

1. Introduce explicit bootstrap states: `unknown | restoring | authenticated | anonymous`.
2. Centralize restore flow so `(app)`, `(admin)`, and `(onboarding)` do not race each other.
3. Route-guard redirects must not fire while bootstrap is `unknown` or `restoring`.
4. Redirect to `/login` only after refresh definitively fails.
5. Preserve current access-token-in-memory and refresh-cookie architecture.

### Story 15.2: Document Intelligence and Year Confirmation Contract

As a user uploading health documents,
I want the system to persist whether a file is a true analysis and whether its date needs year confirmation,
So that dashboard and document flows can distinguish analyses from plain documents and guide me to resolve incomplete dates instead of silently misclassifying them.

Acceptance criteria summary:

1. Persist `document_kind` with exact values `analysis | document | unknown`.
2. Persist `needs_date_confirmation` and `partial_measured_at_text` on documents.
3. Yearless extracted dates must not be converted into fake full timestamps.
4. Add `POST /api/v1/documents/{id}/confirm-date-year`.
5. Confirming the year updates document-level date metadata, all document health values, and document AI interpretation.
6. Document API responses expose the new metadata.

### Story 15.3: Dashboard Filter and Aggregate AI Context

As a dashboard user,
I want the dashboard to operate on the filtered persisted dataset instead of the latest document shortcut,
So that AI notes, chat, and biomarker views reflect the actual active dashboard scope.

Acceptance criteria summary:

1. Add dashboard filter state `all | analysis | document`.
2. Dashboard data loaders honor the active filter.
3. Add dashboard-scoped AI endpoints for interpretation and chat.
4. Dashboard AI context is rebuilt from remaining persisted data after delete, upload, reupload, and year confirmation.
5. When the active filter yields no analyses, biomarker and AI panels show explicit no-analysis states.

### Story 15.4: Sequential Multi-Upload Queue

As a user importing multiple files,
I want to select or drop several files and see each file processed independently in a controlled queue,
So that I can import a batch without repeating the upload flow one file at a time.

Acceptance criteria summary:

1. Upload UI accepts multi-select and multi-drop.
2. Client queue tracks per-file states: `queued | uploading | processing | completed | partial | failed`.
3. Each file reuses the existing single-file upload endpoint and per-document SSE stream.
4. Queue runs sequentially.
5. Retry mode stays single-file when `retryDocumentId` is present.
6. End-of-batch summary reports completed, partial, and failed counts with cabinet links.

### Story 15.5: AI Chat Scroll and Overflow Hardening

As a user having a longer AI conversation,
I want the messages pane to be the only scrolling region and auto-scroll to behave predictably,
So that I can read old messages and continue chatting without layout breakage.

Acceptance criteria summary:

1. `AIChatWindow` uses a fixed-height column layout.
2. Only the messages pane owns vertical scrolling.
3. Input bar and disclaimer remain fixed siblings.
4. Auto-scroll only occurs when the user is already near the bottom.
5. Minimized and maximized modes preserve correct overflow behavior.

### Story 15.6: Core EN/UA Localization

As a user switching between English and Ukrainian,
I want core UI flows to remember my locale across reloads,
So that the app uses my preferred language consistently.

Acceptance criteria summary:

1. Add frontend-only locale store with persistence.
2. Bootstrap locale selection order: saved locale, browser locale, then `en`.
3. Internal locale codes are `en` and `uk`; switch label remains `EN / UA`.
4. Localize auth, dashboard, documents, upload, AI note/chat, and shared action/error strings in touched flows.
5. Backend payloads and validation messages remain unchanged unless explicitly mapped in touched screens.

### Story 15.7: Regression Gate for Stabilized Flows

As the delivery team,
I want automated regression coverage for the stabilized flows,
So that the fixes stay reliable across backend and frontend refactors.

Acceptance criteria summary:

1. Backend coverage exists for classification, yearless-date persistence, year confirmation, and dashboard AI rebuild behavior.
2. Frontend coverage exists for auth restore race, multi-upload queue, filter invalidation, locale persistence, and chat scroll behavior.
3. Acceptance coverage verifies the full end-to-end scenarios defined in the fix plan.

## Dependency Order

1. `15.1` and `15.2` can proceed in parallel.
2. `15.3` depends on `15.2`.
3. `15.4` depends on `15.2`.
4. `15.5` should land after `15.3` to avoid double-touching the chat surface.
5. `15.6` should land after the structural UI work to avoid translation churn.
6. `15.7` closes the epic.

## Definition of Done

- The product no longer silently treats yearless analyses as fully complete.
- Dashboard AI is no longer coupled to `latestDocumentId`.
- Hard reload does not log out authenticated users during bootstrap.
- Multi-file import works over the existing backend contract.
- Long AI conversations remain usable.
- Core EN/UA switching persists across reloads.
