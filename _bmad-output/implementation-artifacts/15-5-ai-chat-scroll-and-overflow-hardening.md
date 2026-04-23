# Story 15.5: AI Chat Scroll and Overflow Hardening

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user having a longer AI conversation**,
I want the messages pane to be the only scrolling region and auto-scroll to behave predictably,
So that I can read old messages and continue chatting without layout breakage.

## Acceptance Criteria

1. **Fixed-height chat shell in normal dashboard state** — `AIChatWindow` uses an explicit fixed-height, column-based layout in its normal dashboard state instead of relying on a `max-height` messages pane alone. The title bar remains visible, the body fills the remaining height, and the default open state remains desktop-first.

2. **Single conversation-history scroll owner** — The conversation history pane (`.hc-ai-chat-messages`) is the only scroll owner for chat-history overflow in open and maximized states. The chat shell/body/dashboard wrapper must not become competing vertical scroll containers when messages grow.

3. **Input bar, hint/error copy, and disclaimer stay fixed** — The toolbar, editor/send row, inline hint or error copy, and disclaimer remain fixed siblings beneath the messages pane while the user scrolls older messages. Long AI responses must not push these controls off-screen.

4. **Auto-scroll respects user intent** — Auto-scroll occurs only when the user is already near the bottom before a new user message, AI placeholder, or streamed AI chunk is appended. If the user has scrolled upward to inspect older messages, incoming chunks must not yank the scroll position back to the bottom. Once the user returns near the bottom, sticky-bottom behavior resumes for subsequent updates.

5. **Minimized and maximized modes keep correct overflow behavior** — Minimized mode shows only the title bar with no stray body/disclaimer scrollbars. Maximized mode preserves the same single-scroll-region behavior as the normal state. Toggling minimize/maximize does not drop the current draft or message history.

## Tasks / Subtasks

- [x] Task 1: Refactor `AIChatWindow` layout so the shell owns height and the messages pane owns history scrolling (AC: 1, 2, 3, 5)
  - [x] Convert the chat root/body to an explicit flex-column layout in both normal and maximized states.
  - [x] Replace the current "messages `max-height` drives layout" approach with a fixed default chat height on `.hc-ai-chat`.
  - [x] Add the necessary `min-height: 0` / `overflow: hidden` rules on parent flex containers so `.hc-ai-chat-messages` can shrink and scroll correctly.
  - [x] Keep title bar, input bar, hint/error region, and disclaimer outside the history scroll container.
  - [x] Preserve the existing minimized-title-bar-only behavior without leftover spacing or scrollbars.

- [x] Task 2: Harden auto-scroll logic around a near-bottom guard instead of unconditional scrolling (AC: 4, 5)
  - [x] Introduce a small threshold-based helper such as `isNearBottom(messagesEl, thresholdPx = 24)` for bottom detection.
  - [x] Capture whether the user is currently "sticky to bottom" before each message append or streamed chunk update.
  - [x] After DOM flush (`tick()` or equivalent), scroll only if the prior state was near-bottom.
  - [x] Update sticky-bottom state on user scroll events so scrolling upward pauses auto-scroll and returning near-bottom resumes it.
  - [x] Reset chat history, draft, active stream, and sticky-scroll state cleanly when the bound identity changes (`documentId` or `dashboard:${documentKind}`).

- [x] Task 3: Preserve existing dual-mode chat behavior while narrowing scope to layout/scroll hardening (AC: 3, 5)
  - [x] Keep the existing `document` vs `dashboard` branching and `streamAiChat` / `streamDashboardChat` contracts unchanged.
  - [x] Preserve dashboard no-context gating (`hasContext === false` disables Send and shows the inline hint).
  - [x] Preserve current markdown rendering, toolbar commands, and AbortController cleanup unless a change is required directly for scroll correctness.
  - [x] Ensure maximize/minimize toggles remain local component state and do not remount the chat or discard draft/history.

- [x] Task 4: Add focused regression coverage for scroll ownership and sticky-bottom behavior (AC: all)
  - [x] Extend `AIChatWindow.test.ts` with cases for near-bottom auto-scroll, no forced scroll when the user is reading older messages, and sticky-bottom resuming after the user scrolls back down.
  - [x] Extend `AIChatWindow.test.ts` to verify maximize/minimize toggles preserve message history and do not break dashboard-mode gating.
  - [x] Add pure helper tests if the scroll-threshold logic is extracted into a separate utility file for easier deterministic testing.
  - [x] Extend dashboard route tests only as needed to confirm the component still renders correctly in populated and filter-empty dashboard branches after the layout refactor.

- [x] Task 5: Verify the fix in the real dashboard surface and keep it bounded (AC: 1, 2, 3, 5)
  - [x] Confirm the dashboard page still mounts `AIChatWindow` below `AIClinicalNote` in both populated and filter-empty branches.
  - [x] Do not touch backend AI routes, rate limiting, or dashboard filter-store semantics.
  - [x] Do not expand scope into chat history persistence, message-cap limits, or broader UI restyling unless a concrete blocker is discovered during implementation.

### Review Findings

- [x] [Review][Patch] Sticky-bottom snapshot can go stale between capture and render [healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte:77-186]
- [x] [Review][Patch] Identity change reset does not clear visible contenteditable draft [healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte:65-75]
- [x] [Review][Patch] Missing identity-change regression coverage for reset/abort behavior [healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts:296-365]
- [x] [Review][Patch] Scroll-ownership regression test currently does not assert overflow ownership [healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts:167-185]

## Dev Notes

### Story Scope and Boundaries

- **This is a frontend-only hardening story.** No backend routes, schemas, rate limits, or AI prompt pipelines need to change for 15.5.
- **Keep the Story 15.3 dual-mode contract intact.** `AIChatWindow` must continue to support both document-scoped and dashboard-scoped chat without splitting into separate components.
- **Do not reopen deferred 10.5 concerns unless they block AC completion.** Message-history capping, orphaned user messages after failed responses, and broader chat UX redesign remain out of scope.
- **Do not alter dashboard filter semantics.** The `all | analysis | document` filter behavior and `hasContext` gating added in 15.3 are load-bearing and should stay unchanged.
- **Do not introduce scoped component CSS or Tailwind structural rewrites.** This component already uses the global `hc-ai-chat-*` style family in `src/app.css`; continue that pattern.
- **Desktop-only MVP constraints still apply.** Do not add mobile/tablet adaptations in this story. [Source: `_bmad-output/project-context.md`, lines 21-27 and 132-138]

### Current Codebase Reality

- `AIChatWindow.svelte` currently scrolls unconditionally through `scrollToBottom()` at [healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte] via the helper at lines 65-68, after user submit at line 109, and after every streamed AI chunk at line 141. This is the main behavioral bug against AC 4.
- The current component structure already places the title bar, messages pane, input bar, optional hint, optional error, and disclaimer in the right DOM order, but the shell/body layout does not yet guarantee single-scroll ownership in the normal open state. [Source: `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte`, lines 158-282]
- `app.css` makes the messages pane scrollable with `max-height: 450px`, but only the maximized variant turns the body into a flex column. The normal variant lacks the fixed-height shell / `min-height: 0` flex pattern needed for reliable overflow ownership. [Source: `healthcabinet/frontend/src/app.css`, lines 3130-3395]
- The input/editor row currently lives in `.hc-ai-chat-inputbar` and the disclaimer sits outside `.hc-ai-chat-body`; this is already compatible with AC 3 and should be preserved while hardening layout. [Source: `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte`, lines 223-282]
- The dashboard mounts `AIChatWindow` in both the populated (`hasFilteredDocuments`) branch and the filter-empty branch, so the refactor must keep both surfaces working. [Source: `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`, lines 241-286]
- Existing component tests cover title rendering, minimize state, empty-send disablement, dashboard no-context hint, and dashboard streaming selection, but they do **not** cover sticky-bottom heuristics or scroll-container ownership yet. [Source: `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts`, lines 24-124]

### Implementation Guardrails

- **Use Svelte 5 runes only.** Keep local UI state with `$state`, derived identity/gating with `$derived`, and side effects minimal. [Source: `_bmad-output/project-context.md`, lines 100-107]
- **Use threshold-based bottom detection, not exact equality.** MDN notes `scrollTop` can be fractional while `scrollHeight` and `clientHeight` are rounded, so bottom checks should use a threshold comparison instead of exact math. Source: https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollHeight
- **Flush DOM updates before applying `scrollTop`.** Svelte’s `tick()` resolves once pending state changes have been applied, making it the correct boundary for post-update scroll adjustments. Source: https://svelte.dev/docs/svelte/svelte#tick
- **Apply `min-height: 0` to column flex items that should allow inner scrolling.** MDN’s flex reference explicitly notes that flex items do not shrink below min-content size unless `min-width`/`min-height` is adjusted. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/flex
- **Keep overflow ownership explicit.** The intended history scroll container should be the only element that becomes a scroll container for message growth; avoid accidental second scroll regions on the shell/body/page. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Overflow
- **Do not change the streaming/auth contract.** `activeController`, `streamAiChat`, and `streamDashboardChat` cleanup behavior should remain intact unless a change is directly required for layout/scroll correctness.
- **Preserve accessibility hooks.** `role="log"`, `aria-live="polite"`, the accessible textbox label, and the visible disclaimer must survive the refactor. [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`, lines 891-898 and 1163-1168]

### File Targets

**Primary modified files:**

- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte` — sticky-bottom logic, scroll event handling, maximize/minimize preservation
- `healthcabinet/frontend/src/app.css` — fixed-height flex layout and overflow ownership for `.hc-ai-chat*`
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts` — new scroll/overflow regression coverage
- `healthcabinet/frontend/src/routes/(app)/dashboard/page.test.ts` — dashboard integration regression coverage, only if needed

**Optional helper extraction if testing warrants it:**

- `healthcabinet/frontend/src/lib/components/health/ai-chat-scroll.ts` or nearby utility module for pure `isNearBottom` / sticky-state helpers

**Do NOT modify unless blocked by a concrete bug:**

- `healthcabinet/backend/app/ai/router.py`
- `healthcabinet/backend/app/ai/service.py`
- `healthcabinet/frontend/src/lib/api/ai.ts`
- `healthcabinet/frontend/src/lib/stores/dashboard-filter.svelte.ts`
- `healthcabinet/frontend/src/lib/components/health/AIClinicalNote.svelte`

### Testing Requirements

- Follow the project rule and run focused frontend tests first; this story should not require backend test changes. [Source: `_bmad-output/project-context.md`, lines 145-170]
- Extend `AIChatWindow.test.ts` with deterministic scroll-metric stubs (`scrollTop`, `scrollHeight`, `clientHeight`) so the sticky-bottom logic is asserted directly.
- Cover at least these cases:
  - user submits while already near bottom -> scroll follows new user message / streamed reply
  - user scrolls upward before a streamed chunk -> no snap-back occurs
  - user returns near bottom -> sticky behavior resumes on subsequent chunks
  - identity change (`documentId` or `documentKind`) clears message history/draft and aborts in-flight stream
  - minimize/maximize toggles do not clear message history or draft
  - dashboard `hasContext=false` still disables Send and shows the inline hint after the refactor
- If JSDOM makes DOM-scroll assertions too brittle inside the Svelte component, extract the threshold helpers into a pure module and test them directly, while leaving a smaller integration assertion in `AIChatWindow.test.ts`.
- Run `npm run test:unit` after implementation. Do not broaden scope into `npm run check` or unrelated test sweeps unless shared types or common CSS infrastructure are touched.

### Previous Story Intelligence

- **Story 10.5** introduced `AIChatWindow` as a dashboard chat surface, originally with auto-scroll behavior and global `hc-ai-chat-*` styling. Its review explicitly changed auto-scroll from `$effect` to `requestAnimationFrame` and deferred unrelated issues like history capping and failed-response cleanup; 15.5 should fix scroll ownership/predictability without reopening those deferrals. [Source: `_bmad-output/implementation-artifacts/10-5-ai-clinical-note-chat-window-integration.md`, lines 53-61 and 96-101]
- **Story 15.3** refactored `AIChatWindow` into a dual-mode component (`document` vs `dashboard`) and added `hasContext` gating. 15.5 must preserve that behavior while hardening layout/scroll. [Source: `_bmad-output/implementation-artifacts/15-3-dashboard-filter-and-aggregate-ai-context.md`]
- **Story 15.4** just landed and confirms Epic 15 work is being reviewed heavily for edge cases. Keep this patch additive and narrow to the chat surface so code review can focus on the actual overflow/scroll bug instead of collateral changes. [Source: `_bmad-output/implementation-artifacts/15-4-sequential-multi-upload-queue.md`, lines 195-209]
- **Story 15.7** will add a broader regression gate later; add the focused chat scroll tests now so 15.7 can verify rather than discover this behavior.

### Git Intelligence Summary

Recent history shows Epic 15 stabilization work touching adjacent surfaces:

```text
8465330 feat: implement upload queue management and UI components
ae0a39f feat: update test cases to include document kind and date confirmation fields; enhance mock data for better coverage
8a0cbfb feat: enhance DocumentDetailPanel with result date and document kind display; add year confirmation functionality
12f4309 feat: enhance cookie security settings and add password visibility toggle in login
945ef13 feat: implement dashboard mode for AI Clinical Note and related components
```

Inference: this repo is in a multi-round stabilization phase. The safest 15.5 implementation is a narrow refactor of one component, one CSS block, and a focused test file, with route-test touch-ups only when they prove the chat still behaves correctly in dashboard mode.

### Latest Technical Information

- **Bottom detection should use a threshold.** MDN’s `scrollHeight` guidance explicitly warns that `scrollTop` can be fractional while `scrollHeight` and `clientHeight` are rounded, so exact bottom equality is unreliable. Source: https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollHeight
- **Flex scroll containers need `min-height: 0`.** MDN’s `flex` reference notes that flex items do not shrink below min-content size by default; for an inner scroll region in a column layout, the parent/child flex items need the usual `min-height: 0` escape hatch. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/flex
- **`tick()` is the right post-update boundary in Svelte.** The Svelte docs state that `tick()` resolves once pending state changes have been applied, which is the correct moment to measure or set the messages pane scroll position. Source: https://svelte.dev/docs/svelte/svelte#tick
- **Overflow ownership should be explicit.** MDN’s overflow guide frames scrollable overflow as something you deliberately assign to a specific scroll container; that principle maps directly to AC 2 for `AIChatWindow`. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Overflow

### Project Structure Notes

- The chat component remains a shared health UI component under `frontend/src/lib/components/health/`.
- Global styling for this surface remains in `frontend/src/app.css`, consistent with Story 10.5 and current repo practice.
- Dashboard route integration stays in `frontend/src/routes/(app)/dashboard/+page.svelte`; do not move the component or create a dashboard-specific clone.
- Component tests remain colocated beside the Svelte component; route-level integration tests stay under the dashboard route test file.

### References

- `_bmad-output/planning-artifacts/flow-stabilization-epic-15.md`, lines 97-109
- `_bmad-output/planning-artifacts/ux-design-specification.md`, lines 891-898 and 1163-1168
- `_bmad-output/project-context.md`, lines 21-27, 100-138, and 145-170
- `_bmad-output/planning-artifacts/architecture.md`, lines 95-101, 520-527, and 808-811
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte`, lines 54-155 and 158-282
- `healthcabinet/frontend/src/app.css`, lines 3077-3395
- `healthcabinet/frontend/src/routes/(app)/dashboard/+page.svelte`, lines 76-80 and 241-286
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts`, lines 24-124
- `_bmad-output/implementation-artifacts/10-5-ai-clinical-note-chat-window-integration.md`
- `_bmad-output/implementation-artifacts/15-3-dashboard-filter-and-aggregate-ai-context.md`
- `_bmad-output/implementation-artifacts/15-4-sequential-multi-upload-queue.md`, lines 195-216

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- None. Implementation hit no HALT conditions; no ambiguous task requirements encountered.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Layout refactor (AC 1, 2, 3, 5).** `.hc-ai-chat` is now an explicit `display: flex; flex-direction: column; height: 540px; overflow: hidden` shell. `.hc-ai-chat-body` adds `flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; overflow: hidden` so the messages pane can own overflow. `.hc-ai-chat-messages` drops `max-height: 450px` and becomes the single scroll container with `flex: 1 1 auto; min-height: 0; overflow-y: auto`. Title bar, input bar, and disclaimer are `flex: 0 0 auto` fixed siblings. Minimized variant pins `height: auto` and hides body/disclaimer; maximized variant overrides positioning with `height: auto` and inherits the same flex shell, so no mode-specific `max-height` override is needed anymore.
- **Sticky-bottom auto-scroll (AC 4, 5).** Added pure `isNearBottom(el, threshold=24)` helper in `ai-chat-scroll.ts` that uses threshold comparison per MDN guidance on fractional `scrollTop`. New `stickyBottom` `$state` is updated by an `onscroll` handler on `.hc-ai-chat-messages`. Before every `messages[]` mutation (user submit, AI placeholder append, streamed chunk update) we capture `wasSticky`, then `await tick()` to flush the DOM, then `scrollTop = scrollHeight` only if `wasSticky` was true. Scrolling upward pauses auto-scroll; returning near bottom flips sticky back to `true` and subsequent chunks resume following. Replaces the previous unconditional `requestAnimationFrame(scrollToBottom)` calls.
- **Identity reset (AC 4).** The existing `$effect(identity)` block now also resets `stickyBottom = true` alongside clearing messages, draft, streaming state, and aborting the active controller. A fresh thread starts sticky.
- **Dual-mode preservation (AC 3, 5).** No changes to `document` vs `dashboard` branching, `streamAiChat` / `streamDashboardChat` contracts, `hasContext` gating, markdown rendering, toolbar commands, `AbortController` cleanup, or minimize/maximize local-state semantics. Dashboard mounts `AIChatWindow` unchanged in both populated and filter-empty branches at `routes/(app)/dashboard/+page.svelte:264-270` and `:284-286`.
- **Test coverage (AC all).** Added `ai-chat-scroll.test.ts` with 9 pure helper tests covering null/undefined, at-bottom, within-threshold, past-threshold, exact-boundary, custom threshold, fractional `scrollTop`. Extended `AIChatWindow.test.ts` with 7 new component tests: single-scroll-container structure, fixed shell sibling layout, auto-scroll when near bottom, no snap-back when scrolled up, sticky-bottom resumes when user returns, minimize-then-restore preserves message history, maximize toggle preserves history and draft. Existing 7 tests (title, minimize, input/send render, empty-send disabled, axe audit, dashboard no-context hint, dashboard stream) all still pass.
- **Bounded scope verified.** Only touched files live in `healthcabinet/frontend/src/app.css` and `healthcabinet/frontend/src/lib/components/health/` (AIChatWindow + new helper pair). No backend routes, no rate limiting, no dashboard filter store, no AIClinicalNote changes, no API client changes. Per story boundary rules.
- **Test results.** `docker compose exec frontend npm run test:unit` — full suite passed: **67 files / 722 tests, 0 failures**. No regressions observed in adjacent surfaces (dashboard route tests, AI clinical note tests, document page tests, all remained green).

### File List

**Modified**

- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.svelte` — added `tick` + `isNearBottom` imports, `stickyBottom` `$state`, `handleMessagesScroll`, `applyStickyScroll(wasSticky)` helper, identity-reset clears `stickyBottom`, replaced three `requestAnimationFrame(scrollToBottom)` sites with sticky-aware applyStickyScroll calls, wired `onscroll` listener on `.hc-ai-chat-messages`.
- `healthcabinet/frontend/src/app.css` — `.hc-ai-chat` fixed-height flex-column shell, `.hc-ai-chat-body` flex-column overflow-hidden with `min-height: 0`, `.hc-ai-chat-messages` single scroll owner (removed `max-height: 450px`), title bar / inputbar / disclaimer marked `flex: 0 0 auto`, minimized variant uses `height: auto`, maximized variant simplified to positioning-only override (inherits base flex shell).
- `healthcabinet/frontend/src/lib/components/health/AIChatWindow.test.ts` — added `stubScrollMetrics` + `singleChunkResponse` + `settleStream` helpers and 7 new tests covering scroll ownership, sticky-bottom behavior, and minimize/maximize state preservation.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 15-5 status transitioned `ready-for-dev` → `in-progress` → `review`, last_updated bumped.
- `_bmad-output/implementation-artifacts/15-5-ai-chat-scroll-and-overflow-hardening.md` — all task checkboxes marked complete, Dev Agent Record + Change Log filled, File List populated, Status set to `review`.

**Added**

- `healthcabinet/frontend/src/lib/components/health/ai-chat-scroll.ts` — pure `isNearBottom(el, threshold=24)` helper with `DEFAULT_NEAR_BOTTOM_THRESHOLD_PX` export, documented against MDN `scrollHeight` fractional-value guidance.
- `healthcabinet/frontend/src/lib/components/health/ai-chat-scroll.test.ts` — 9 deterministic unit tests for the helper covering null/undefined, exactly at bottom, within threshold, past threshold, boundary, custom threshold, and fractional `scrollTop` inputs.

## Change Log

| Date       | Change                                                                                                                                  | Author |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 2026-04-22 | Initial implementation — fixed-height flex-column chat shell, single messages-pane scroll owner, sticky-bottom auto-scroll with user-intent respect, identity-reset state clearing, 16 new regression tests across helper + component. | Dev    |
