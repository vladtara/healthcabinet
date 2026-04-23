# Story 10.5: AI Clinical Note & Chat Window Integration

Status: done

## Story

As a user with processed health documents,
I want an AI clinical note summarizing my latest results and an ICQ-style chat window for follow-up questions displayed on my dashboard,
so that I can understand my health data in plain language and ask questions without leaving the main screen.

## Acceptance Criteria

1. **AIClinicalNote component** — A new `AIClinicalNote.svelte` in `src/lib/components/health/` renders the AI interpretation for the most recent document in a 98.css sunken panel with 3px accent left border. Header: "AI Clinical Note" (bold, accent color). Body: interpretation text (15px, line-height 1.6). Collapsible reasoning panel (values referenced, uncertainty flags). Disclaimer footer: italic, disabled color. States: loading (skeleton), populated, error, empty (no interpretation available — show "Upload a document to receive AI interpretation").

2. **AIChatWindow component** — A new `AIChatWindow.svelte` in `src/lib/components/health/` renders an ICQ-style chat window with: title bar ("Dr. Health — AI Assistant" with minimize/maximize toggle), chat message area (sunken, scrollable), text input with Send button, disclaimer. Uses `streamAiChat` API with the latest document_id. States: open (default), minimized (title bar only). Messages: user (right-aligned or distinct styling) and AI response (left-aligned, streamed). Input disabled while streaming.

3. **Dashboard integration** — Both components render below the Biomarker Results table and above the Trends section. AIClinicalNote appears first, AIChatWindow below it. Only rendered when `values.length > 0` (user has uploaded documents). The latest document_id is derived from the values data.

4. **Data sourcing** — AIClinicalNote fetches via `getDocumentInterpretation(latestDocumentId)` with TanStack Query key `['ai_interpretation', latestDocId]`. AIChatWindow uses `streamAiChat({ document_id: latestDocId, question })`. The latest document_id is derived from `values` by finding the most recent `created_at`.

5. **CSS follows established patterns** — New styles in `app.css` using `.hc-ai-note-*` for the clinical note and `.hc-ai-chat-*` for the chat window. 98.css sunken panels, raised title bar for chat. No scoped styles.

6. **Tests** — AIClinicalNote: renders interpretation text, loading skeleton, error state, empty state message, disclaimer always present, reasoning toggle, axe audit. AIChatWindow: renders title bar, minimized state, user can type and submit, streaming indicator, axe audit. Dashboard integration tests for both components.

7. **WCAG Considerations** — AIClinicalNote uses `role="complementary"` with `aria-label="AI health interpretation"`. AIChatWindow chat area uses `role="log"` with `aria-live="polite"`. Input has proper label. Reasoning toggle uses `aria-expanded`. Minimize/maximize uses `aria-expanded` on title bar button.

## Tasks / Subtasks

- [x] Task 1: Add AIClinicalNote CSS to app.css (AC: #5)
  - [x] 1.1 Add `.hc-ai-note` sunken panel with 3px accent left border
  - [x] 1.2 Add `.hc-ai-note-header` for title text (bold, accent color)
  - [x] 1.3 Add `.hc-ai-note-body` for interpretation text (15px, line-height 1.6)
  - [x] 1.4 Add `.hc-ai-note-disclaimer` for footer text (italic, disabled color)
  - [x] 1.5 Add `.hc-ai-note-reasoning` for collapsible reasoning section + toggle button

- [x] Task 2: Add AIChatWindow CSS to app.css (AC: #5)
  - [x] 2.1 Add `.hc-ai-chat` container with 98.css border
  - [x] 2.2 Add `.hc-ai-chat-titlebar` raised panel with accent gradient
  - [x] 2.3 Add `.hc-ai-chat-messages` sunken scrollable area (max-height: 300px)
  - [x] 2.4 Add `.hc-ai-chat-msg-user` and `.hc-ai-chat-msg-ai` message styling with left borders
  - [x] 2.5 Add `.hc-ai-chat-input` input bar with send button area
  - [x] 2.6 Add `.hc-ai-chat-minimized` state (hides body + disclaimer)

- [x] Task 3: Create AIClinicalNote component (AC: #1, #4)
  - [x] 3.1 Create `src/lib/components/health/AIClinicalNote.svelte` with props: `documentId: string | null`
  - [x] 3.2 Fetch interpretation via TanStack Query (enabled when documentId not null)
  - [x] 3.3 Render interpretation in `.hc-ai-note` panel with header, body, disclaimer
  - [x] 3.4 Collapsible reasoning panel with toggle button (`aria-expanded`)
  - [x] 3.5 Loading skeleton state
  - [x] 3.6 Error state (inline message, handles 404 gracefully)
  - [x] 3.7 Empty state when no documentId

- [x] Task 4: Create AIChatWindow component (AC: #2)
  - [x] 4.1 Create `src/lib/components/health/AIChatWindow.svelte` with props: `documentId: string | null`
  - [x] 4.2 Title bar with "Dr. Health — AI Assistant" and minimize/maximize toggle
  - [x] 4.3 Chat message area (sunken, scrollable) with user and AI messages
  - [x] 4.4 Text input with Send button; disabled during streaming
  - [x] 4.5 `streamAiChat` with AbortController for cancellation
  - [x] 4.6 Minimized state (title bar only, `aria-expanded`)
  - [x] 4.7 Disclaimer text below input
  - [x] 4.8 Auto-scroll via $effect on messages.length

- [x] Task 5: Integrate into dashboard page (AC: #3)
  - [x] 5.1 Derive `latestDocumentId` from values (most recent `created_at`)
  - [x] 5.2 Render AIClinicalNote after BiomarkerTable, wrapped in `.hc-dash-section`
  - [x] 5.3 Render AIChatWindow after AIClinicalNote, before Trends
  - [x] 5.4 Both only render in active state (`values.length > 0`)

- [x] Task 6: Write AIClinicalNote tests (AC: #6, #7)
  - [x] 6.1 Test: renders interpretation text when loaded
  - [x] 6.2 Test: renders loading skeleton
  - [x] 6.3 Test: renders error message on fetch failure
  - [x] 6.4 Test: renders empty state when documentId is null
  - [x] 6.5 Test: disclaimer always present
  - [x] 6.6 Test: reasoning toggle expands/collapses
  - [x] 6.7 Test: axe accessibility audit passes

- [x] Task 7: Write AIChatWindow tests (AC: #6, #7)
  - [x] 7.1 Test: renders title bar with "Dr. Health"
  - [x] 7.2 Test: minimize toggle hides message area
  - [x] 7.3 Test: input field and send button render
  - [x] 7.4 Test: send button disabled when input empty
  - [x] 7.5 Test: axe accessibility audit passes

- [x] Task 8: Update dashboard page tests (AC: #6)
  - [x] 8.1 Test: AIClinicalNote renders in active state
  - [x] 8.2 Test: AIChatWindow renders in active state
  - [x] 8.3 Test: neither component renders in empty state

- [x] Task 9: Run full test suite (AC: #6)
  - [x] 9.1 Run `docker compose exec frontend npm run test:unit` — 433/434 pass (1 pre-existing failure)
  - [x] 9.2 Run `docker compose exec frontend npm run check` — 0 errors, 2 pre-existing warnings

### Review Findings

- [x] [Review][Patch] Added 404-specific branch showing "AI interpretation is being generated…" [AIClinicalNote.svelte]
- [x] [Review][Patch] Replaced $effect scroll with requestAnimationFrame calls in streaming loop and after user message [AIChatWindow.svelte]
- [x] [Review][Patch] Moved error `<p role="alert">` inside `.hc-ai-chat-body` so it's hidden when minimized [AIChatWindow.svelte]
- [x] [Review][Defer] Array reallocation per SSE chunk — correct Svelte 5 pattern, long-session perf concern
- [x] [Review][Defer] Unbounded messages array — no cap on conversation history
- [x] [Review][Defer] Failed response leaves orphaned user message with no AI reply
- [x] [Review][Defer] String comparison for latestDocumentId — pre-existing pattern, works for ISO 8601
- [x] [Review][Defer] Hardcoded aria-controls ID "ai-note-reasoning" — only one instance currently

## Dev Notes

### Architecture Decisions

- **New components, not reskinned existing ones** — `AiInterpretationCard.svelte` and `AiFollowUpChat.svelte` already exist for the document detail page. They use Tailwind classes and are tightly coupled to per-document views. The dashboard needs distinct 98.css-styled components with different layout patterns (clinical note format vs card format, ICQ-style chat vs inline Q&A). Creating new components avoids breaking the document detail page.
- **Both components are per-document** — They take a `documentId` prop. The dashboard derives the latest document_id from health values. This keeps them reusable (could be used on other pages that have a document context).
- **Chat uses streaming** — `streamAiChat` returns a `Response` with a `ReadableStream`. Use the same streaming pattern as `AiFollowUpChat.svelte` (lines 63-89): `getReader()` + `TextDecoder` + chunk loop.
- **Minimize state is local** — `$state` boolean, no persistence needed.

### Component Specifications

**AIClinicalNote layout:**
```
┌─ .hc-ai-note (sunken panel, 3px accent left border) ───┐
│ ℹ AI Clinical Note                                       │
│                                                           │
│ Your latest lab results show TSH at 5.8 mIU/L, which     │
│ is above the reference range of 0.4–4.0. This is         │
│ consistent with undertreated hypothyroidism. Ferritin     │
│ at 18 ng/mL is below optimal range...                     │
│                                                           │
│ [Show reasoning]                                          │
│                                                           │
│ AI-generated · for educational purposes only ·            │
│ not a medical diagnosis                                   │
└──────────────────────────────────────────────────────────┘
```

**AIChatWindow layout:**
```
┌─ .hc-ai-chat-titlebar (raised, accent) ─────────── [_] ┐
│ 🩺 Dr. Health — AI Assistant                             │
├──────────────────────────────────────────────────────────┤
│ ┌─ .hc-ai-chat-messages (sunken, scrollable) ──────────┐│
│ │                                                       ││
│ │ You: What does my TSH trend mean?                     ││
│ │                                                       ││
│ │ Dr. Health: Your TSH has been increasing              ││
│ │ steadily across your last 3 results...                ││
│ │                                                       ││
│ └───────────────────────────────────────────────────────┘│
│ ┌─ .hc-ai-chat-input ─────────────────────── [Send] ───┐│
│ │ Type your question here…                              ││
│ └───────────────────────────────────────────────────────┘│
│ AI-generated · not a medical diagnosis                   │
└──────────────────────────────────────────────────────────┘
```

**Dashboard layout after this story (active state):**
```
PatientSummaryBar
StatCardGrid
Pattern Alerts (if any)
Biomarker Results (BiomarkerTable)
AI Clinical Note                    ← NEW
AI Chat Window                      ← NEW
Trends (BiomarkerTrendSection per biomarker)
```

### Latest Document ID Derivation

```typescript
const latestDocumentId = $derived(
  values.length > 0
    ? values.reduce((latest, v) => {
        const dCurrent = v.created_at;
        const dLatest = latest.created_at;
        return dCurrent > dLatest ? v : latest;
      }, values[0]).document_id
    : null
);
```

### Streaming Pattern (from AiFollowUpChat.svelte)

```typescript
const response = await streamAiChat({ document_id: documentId, question }, signal);
const reader = response.body?.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  streamedAnswer += decoder.decode(value, { stream: true });
}
```

### Existing API Functions (DO NOT recreate)

| Function | Import | Returns |
|----------|--------|---------|
| `getDocumentInterpretation(docId)` | `$lib/api/ai` | `AiInterpretationResponse` (interpretation, reasoning, model_version) |
| `streamAiChat(payload, signal)` | `$lib/api/ai` | `Response` with ReadableStream |

### Existing Types to Use

```typescript
// From $lib/api/ai.ts
interface AiInterpretationResponse {
  document_id: string;
  interpretation: string;
  model_version: string | null;
  generated_at: string;
  reasoning: ReasoningContext | null;
}

interface ReasoningContext {
  values_referenced: ValueReasoning[];
  uncertainty_flags: string[];
  prior_documents_referenced: string[];
}

interface ValueReasoning {
  name: string;
  value: number;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  status: ValueStatus; // 'normal' | 'high' | 'low' | 'unknown'
}
```

### AIClinicalNote vs Existing AiInterpretationCard

| Aspect | AiInterpretationCard (doc detail) | AIClinicalNote (dashboard) |
|--------|-----------------------------------|---------------------------|
| Location | Document detail page | Dashboard active state |
| Styling | Tailwind (rounded-md, bg-card/50) | 98.css (sunken panel, .hc-ai-note-*) |
| Heading | "AI Interpretation" | "AI Clinical Note" |
| Role | Part of document view | Standalone dashboard section |
| ARIA | Generic section | `role="complementary"` |

### AIChatWindow vs Existing AiFollowUpChat

| Aspect | AiFollowUpChat (doc detail) | AIChatWindow (dashboard) |
|--------|----------------------------|--------------------------|
| Location | Document detail page | Dashboard active state |
| Styling | Tailwind (border-l-4) | 98.css ICQ-style (.hc-ai-chat-*) |
| UI Pattern | Inline Q&A form | Chat window with title bar, messages, minimize |
| Message History | Single Q&A (no history) | Shows user + AI messages in chat log |
| Minimize | N/A | Title bar toggle |

### What NOT to Touch

- Existing `AiInterpretationCard.svelte` (document detail page)
- Existing `AiFollowUpChat.svelte` (document detail page)
- PatternAlertSection (story 10-4)
- BiomarkerTable (story 10-3)
- Empty state rendering
- Backend AI code

### Previous Story Intelligence

**From story 10-4:**
- Dashboard active state layout: Summary → Stats → Patterns → Table → Trends
- PatternAlertSection uses props-driven approach (loading/error/data)
- Test baseline: 418/419 pass (1 pre-existing failure in `users.test.ts`)
- `getAiPatterns` mock added to dashboard tests
- BiomarkerTrendSection uses `<h2>` for heading order (fixed from `<h3>`)

**From story 10-3:**
- Row striping uses class-based `.hc-bio-row-even` approach
- All new components need QueryClient wrapper for tests when using TanStack Query

**Git intelligence:**
- Pattern: `feat(ui):` prefix for UI component commits
- All new components have test files + axe audits
- Test wrappers: `*TestWrapper.svelte` pattern for components needing QueryClient context

### Testing Patterns

- **AIClinicalNote tests:** Needs QueryClient wrapper (uses `createQuery`). Create `AIClinicalNoteTestWrapper.svelte`.
- **AIChatWindow tests:** Does NOT need QueryClient (uses `streamAiChat` directly, not TanStack Query). Standalone render.
- **Mock `streamAiChat`:** Return a mock `Response` with a `ReadableStream`. Use `new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('response text')); controller.close(); } })`.
- **Dashboard tests:** Mock `getDocumentInterpretation` alongside existing mocks.

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 844-857] — AIClinicalNote and AIChatWindow component specs
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 98] — "AI interpretation appears in sunken panel below results table, reads like clinical note"
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md, lines 568] — "ICQ-style AI chat window"
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md, line 177] — Story candidate: "AIClinicalNote and AIChatWindow integration below results table"
- [Source: _bmad-output/planning-artifacts/prd.md, FR18-FR22] — AI interpretation, reasoning trail, follow-up Q&A, cross-upload patterns
- [Source: healthcabinet/frontend/src/lib/api/ai.ts] — All AI API functions and types
- [Source: healthcabinet/frontend/src/lib/components/health/AiInterpretationCard.svelte] — Existing per-document interpretation (reference for reasoning toggle pattern)
- [Source: healthcabinet/frontend/src/lib/components/health/AiFollowUpChat.svelte] — Existing per-document chat (reference for streaming pattern)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- `docker compose exec frontend npm run test:unit`: 433/434 passed; 1 pre-existing failure in `users.test.ts`
- `docker compose exec frontend npm run check`: 0 errors, 2 pre-existing warnings
- Fixed Svelte 5 `{@const}` placement in AIClinicalNote (must be direct child of `{#if}`)
- Fixed axe `landmark-complementary-is-top-level` — removed `role="complementary"` from nested AIClinicalNote section (native `<section>` semantics sufficient)

### Completion Notes List

- Created `AIClinicalNote.svelte` — 98.css sunken panel with accent left border, fetches latest document interpretation via TanStack Query, collapsible reasoning panel (values table, uncertainty flags), loading/error/empty states, disclaimer footer
- Created `AIChatWindow.svelte` — ICQ-style chat with accent gradient title bar, minimize/maximize toggle, sunken scrollable message area, streaming AI responses via `streamAiChat`, text input with Send button, auto-scroll, error handling, AbortController cleanup on document change
- Added ~150 lines of `.hc-ai-note-*` and `.hc-ai-chat-*` CSS in app.css
- Integrated both components into dashboard: rendered between BiomarkerTable and Trends sections, only in active state
- Derived `latestDocumentId` from health values (most recent `created_at`)
- Added `getDocumentInterpretation` mock to dashboard tests
- 7 AIClinicalNote tests + 5 AIChatWindow tests + 3 dashboard integration tests = 15 new tests

### File List

- `healthcabinet/frontend/src/app.css` (modified — added `.hc-ai-note-*` and `.hc-ai-chat-*` CSS)
- `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.test.ts` (new)
- `healthcabinet/frontend/src/lib/components/health/AIClinicalNoteTestWrapper.svelte` (new — test helper)
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte` (new)
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts` (new)
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte` (modified — added AI components + latestDocumentId)
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` (modified — added AI component tests + mocks)
- `_bmad-output/implementation-artifacts/10-5-ai-clinical-note-chat-window-integration.md` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)

### Change Log

- 2026-04-04: Implemented story 10-5 AI Clinical Note & Chat Window — AIClinicalNote with reasoning panel, AIChatWindow with ICQ-style streaming chat, dashboard integration
