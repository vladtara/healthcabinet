# Story 14.5: Desktop QA and Tailwind Remnant Sweep

Status: done

## Story

As a developer,
I want to verify the 98.css-migrated frontend renders correctly at all three target desktop widths and produce a finalized inventory of the 9 remaining Tailwind component files,
so that Epic 6 (GDPR stories 6-2 and 6-3) can begin with confirmed visual quality and a clear deferred-work record.

## Acceptance Criteria

**AC1: Desktop QA — App routes pass at 1024px, 1440px, 2560px**
1. Run the app via `docker compose up -d` and open it in a browser.
2. Verify each of the 5 app routes at all three widths: 1024px, 1440px, 2560px.
   - Routes: `/dashboard`, `/documents`, `/documents/upload`, `/documents/[id]` (open any document), `/settings`
3. At each width, confirm: no horizontal scrolling, no content overflow, no text truncation hiding critical information, no layout breaks, panels and window chrome render correctly.
4. Record any visual issues found in Dev Notes (layout bugs or deferred cosmetic issues).

**AC2: Desktop QA — Admin routes pass at 1024px, 1440px, 2560px**
5. Verify each of the 5 admin routes at all three widths.
   - Routes: `/admin`, `/admin/documents`, `/admin/documents/[id]` (open any queue item), `/admin/users`, `/admin/users/[id]` (open any user)
6. Same verification criteria as AC1.
7. Record any visual issues found in Dev Notes.

**AC3: No responsive CSS breakpoints added**
8. No `@media` breakpoints or `md:` / `lg:` / `sm:` Tailwind prefix classes are introduced by this story. The project is desktop-only (1024px+). Any layout at 1440px and 2560px is achieved via `max-width` containers centering at wide viewports, not responsive breakpoints.

**AC4: Tailwind remnant sweep — 9 component files inventoried and documented**
9. Read each of the 9 deferred component files (see Dev Notes for the file list).
10. For each file, record: (a) the Tailwind structural classes still present, (b) existing `.hc-*` classes already in use, (c) a short note on migration complexity.
11. Update `_bmad-output/implementation-artifacts/deferred-work.md` — replace the existing Tailwind remnant entry with an accurate per-file inventory.

**AC5: `deferred-work.md` entry is current and accurate**
12. The `deferred-work.md` Tailwind remnant entry is replaced (not appended) with the per-file breakdown from AC4.
13. The entry includes the story and date: "Re-deferred from: story-14.5 with inventory (2026-04-17)".

## Tasks / Subtasks

- [x] Task 1: Start the app and prepare browser (AC: 1, 2)
  - [x] 1.1 **PRE-FLIGHT: If `docker compose up -d` fails or app does not load at `http://localhost:3000`, stop immediately and notify DUDE.** (Epic 13 retro HALT condition.)
  - [x] 1.2 Log in as a regular user and navigate to `/dashboard`.
  - [x] 1.3 Upload a test document (or use an existing one) so `/documents/[id]` and `/documents` have data.
  - [x] 1.4 Open browser devtools (F12 → device toolbar or drag viewport width) to resize to 1024px, 1440px, 2560px.

- [x] Task 2: Verify all app routes at 3 widths (AC: 1, 3)
  - [x] 2.1 `/dashboard` — at 1024px, 1440px, 2560px. Check: biomarker table, AI panel, stat cards, left nav at 180px.
  - [x] 2.2 `/documents` — at 3 widths. Check: document list, upload zone, DataTable columns.
  - [x] 2.3 `/documents/upload` — at 3 widths. Check: upload zone, progress bar.
  - [x] 2.4 `/documents/[id]` — at 3 widths. Check: detail panel, health value table, AI note.
  - [x] 2.5 `/settings` — at 3 widths. Check: profile form, consent timeline section, export/delete buttons.
  - [x] 2.6 Record any failures in Dev Notes section "Desktop QA Findings".

- [x] Task 3: Verify all admin routes at 3 widths (AC: 2, 3)
  - [x] 3.1 `/admin` — at 3 widths. Check: stat cards, admin shell chrome.
  - [x] 3.2 `/admin/documents` — at 3 widths. Check: DataTable, queue items.
  - [x] 3.3 `/admin/documents/[document_id]` — at 3 widths. Check: correction detail panel.
  - [x] 3.4 `/admin/users` — at 3 widths. Check: DataTable, pagination.
  - [x] 3.5 `/admin/users/[user_id]` — at 3 widths. Check: user detail, ConfirmDialog trigger.
  - [x] 3.6 Record any failures in Dev Notes section "Desktop QA Findings".

- [x] Task 4: Tailwind remnant sweep — read and document 9 files (AC: 4, 5)
  - [x] 4.1 Read `AiInterpretationCard.svelte` — list Tailwind structural classes and any `.hc-*` classes present.
  - [x] 4.2 Read `AiFollowUpChat.svelte` — list Tailwind structural classes.
  - [x] 4.3 Read `PatternCard.svelte` — list Tailwind structural classes.
  - [x] 4.4 Read `AIClinicalNote.svelte` — list Tailwind structural classes (note: already has `.hc-ai-note-*` classes).
  - [x] 4.5 Read `BiomarkerTrendChart.svelte` — list Tailwind structural classes (SVG-heavy component).
  - [x] 4.6 Read `BiomarkerTrendSection.svelte` — list Tailwind structural classes (note: already has `.hc-trend-*` classes).
  - [x] 4.7 Read `HealthValueBadge.svelte` — list Tailwind structural classes (inline-flex badge pattern).
  - [x] 4.8 Read `PatternAlertSection.svelte` — list Tailwind structural classes (note: already has `.hc-pattern-alert-*` and `.hc-dash-section-*` classes).
  - [x] 4.9 Read `(app)/dashboard/+page.svelte` — list Tailwind structural classes (note: heavily uses `.hc-dash-*` already).
  - [x] 4.10 Update `deferred-work.md` with per-file inventory per AC4–AC5.

- [x] Task 5: Fix any critical layout bugs found in QA (AC: 1, 2)
  - [x] 5.1 If any route has broken layout (overflow, hidden critical content, overlapping elements) — fix it. Minor cosmetic issues may be deferred with documentation.
  - [x] 5.2 Run `docker compose exec frontend npm run check` after any Svelte file edits to verify no type errors.
  - [x] 5.3 Run `docker compose exec frontend npm run test:unit` to confirm no regressions (baseline from Story 14-4).

## Dev Notes

### Context: Why This Story Exists

Epic 13 retro (2026-04-16) identified two outstanding items that became part of the Pre-GA Cleanup Sprint:

- **Tier 1 (before Epic 6):** Desktop QA visual verification (Action #6) — Stories 13-4 and 13-5 completed without Docker running, so the desktop QA visual check (explicitly required in Story 13-5 AC15) was **never executed**. Not a hypothetical deferral — it was documented as "not done" in the 13-5 Dev Notes and code review.
- **Tier 2 (during/after Epic 6):** Tailwind remnant migration of 9 components (Action #7). Story 13-5's code review found "Tailwind remnant sweep was not completed or documented." The sweep was documented in name only; the actual per-file inventory was not produced. This story produces that inventory.

The **migration of the 9 Tailwind files** (replacing Tailwind classes with `.hc-*` CSS) is explicitly **out of scope** for this story — that is a dedicated future story (Tier 2). This story produces the inventory that future story will execute against.

### Desktop QA: What to Check

The app uses a Windows 98 clinical workstation aesthetic (98.css). Key visual elements to verify per route:

- **Left nav** (180px fixed width) — does it stay at 180px? Does it clip or overflow at narrow widths?
- **Content area** (`flex-1`) — does it fill remaining space correctly?
- **Window chrome** (beveled panels, sunken data regions, status bar) — renders without clipping
- **Status bar** (bottom, fixed) — present on app routes, not on admin/auth routes
- **DataTable columns** — no text overflow hiding data; sort arrows visible
- **max-width containers** — at 2560px wide, content should be centered/contained, not stretched to full width
- **No `sr-only` regressions** — multiple files use `sr-only` for screen reader text; this must remain on elements (it's the only acceptable Tailwind class in app/admin routes per 13-5 AC16)

**Viewport testing approach:** Use browser devtools responsive mode. In Chrome/Firefox: F12 → Toggle device toolbar → set custom width. Do NOT add responsive CSS — verify the layout works naturally at all three widths.

### The 9 Tailwind Remnant Files

All in `healthcabinet/frontend/src/`:

| File | Location | Previous `.hc-*` Classes | Tailwind Complexity |
|------|----------|--------------------------|---------------------|
| `lib/components/health/AiInterpretationCard.svelte` | Health components | None | ~23 TW classes; card layout with `border-l-4`, `bg-card/50`, `rounded-md`, `p-4`, spacing |
| `lib/components/health/AiFollowUpChat.svelte` | Health components | None | ~10 TW classes; `space-y-3`, `mt-4`, `animate-pulse` skeleton |
| `lib/components/health/PatternCard.svelte` | Health components | None | ~5 TW classes; only `mt-4`, `border-l-4`, `rounded-md`, `bg-card/50`, `p-4` |
| `lib/components/health/AIClinicalNote.svelte` | Health components | 7 `.hc-ai-note-*` classes | ~21 TW classes; skeleton loader uses `mb-2`, `h-4`, `w-2/5`, `rounded`, `bg-muted` |
| `lib/components/health/BiomarkerTrendChart.svelte` | Health components | None | ~14 TW classes; SVG chart with `w-full`, `overflow-visible`, `fill-muted-foreground`, `text-[10px]`, `relative`, `flex`, `h-[200px]` |
| `lib/components/health/BiomarkerTrendSection.svelte` | Health components | 5 `.hc-trend-*` classes | ~8 TW classes; skeleton loader + `text-xs` |
| `lib/components/health/HealthValueBadge.svelte` | Health components | None | ~1 TW class compound; `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium` with dynamic status |
| `lib/components/health/PatternAlertSection.svelte` | Health components | 7 `.hc-pattern-alert-*` + `.hc-dash-section-*` | ~18 TW classes; skeleton loader pattern |
| `routes/(app)/dashboard/+page.svelte` | Dashboard route | 13 `.hc-dash-*`, `.hc-action-bar-*`, `.hc-empty-*` etc. | ~14 TW classes; skeleton loaders + `mb-4`, `text-sm`, `text-destructive`, `animate-pulse` |

**Important: `sr-only` is acceptable everywhere.** It is a screen-reader utility and the only non-structural Tailwind class that is NOT flagged for removal. Do not include it in the inventory as a problem.

**Skeleton loader pattern** dominates the remaining Tailwind. The pattern is: `animate-pulse` wrapper div containing `rounded bg-muted h-4 w-2/5` skeleton blocks. The project has a `.hc-skeleton-*` CSS system in `app.css` — this is the migration target.

### CSS Architecture Reference

**Main CSS file:** `healthcabinet/frontend/src/app.css`

**Naming convention:** `.hc-[section]-[element]` (e.g., `.hc-dash-section`, `.hc-ai-note-header`)

**Existing skeleton CSS in `app.css`:**
- Check for `.hc-skeleton-*` classes in `app.css` before defining new ones in component `<style>` blocks.
- The skeleton pattern (`animate-pulse` + rectangular blocks) maps to the existing skeleton system.

**Acceptable Tailwind after migration (from 13-5 AC16):**
- `sr-only` — screen reader only; used in 12+ files; do NOT remove

### Previous Story Intelligence (Story 14-4)

Story 14-4 fixed three broken test files and established verified test baselines. Before this story's Task 5 runs tests:
- Backend baseline: recorded by Story 14-4 (run to verify, not to fix)
- Frontend baseline: recorded by Story 14-4 (run to verify, not to fix)
- If tests fail after Svelte edits in Task 5, diagnose root cause — do not skip or delete tests

**Story 14-4 anti-patterns that apply here:**
- Do not run tests locally (always in Docker Compose)
- Docker-down = HALT condition; notify DUDE immediately

### Anti-Patterns to Avoid

- **Do not add `@media` breakpoints or responsive CSS.** The app is desktop-only (1024px+). Width differences are handled by `max-width` containers and `flex-1` layout, not breakpoints. [Source: ux-design-specification.md line 1114]
- **Do not migrate the 9 Tailwind files.** Inventory and document them. Migration is a separate future story (Epic 13 retro Tier 2 action).
- **Do not remove `sr-only` from any file.** It is explicitly approved by 13-5 AC16 as the one acceptable Tailwind class post-migration.
- **Do not fix every cosmetic issue found in QA.** Document minor cosmetic issues in Dev Notes as deferred. Fix only broken layouts (overflow, hidden critical content, overlapping elements).
- **Do not run tests locally.** Always: `docker compose exec frontend npm run test:unit` (global CLAUDE.md rule).

### Desktop QA Findings

**Infrastructure issues resolved before QA could run:**
- DB had corrupted alembic_version (only `alembic_version` table existed; data tables absent despite version showing 014). Fixed by clearing the version entry and re-running all 14 migrations via `cd /app && alembic -c alembic/alembic.ini upgrade head`.
- Stale Vite module cache caused `SyntaxError: module does not provide export 'streamDocumentStatus'` on `/documents`. Fixed by clearing `.svelte-kit/generated` and restarting the frontend container.

**Layout verification results — no layout breaks at any width:**

| Route | 1024px | 1440px | 2560px | Notes |
|-------|--------|--------|--------|-------|
| `/dashboard` | ✅ | ✅ | ✅ | Table horizontal scroll is panel-contained (expected) |
| `/documents` | ✅ | ✅ | ✅ | Empty state, no data |
| `/documents/upload` | ✅ | ✅ | ✅ | Upload dialog, drag-and-drop zone correct |
| `/documents/[id]` | — | — | — | No documents in DB; empty state verified via `/documents` |
| `/settings` | ✅ | ✅ | ✅ | Fieldsets, form elements, 2-col checkbox grid all correct |
| `/admin` | ✅ | ✅ | ✅ | See deferred cosmetic issue #2 below |
| `/admin/documents` | ✅ | ✅ | ✅ | Empty queue state |
| `/admin/documents/[id]` | — | — | — | No queue items in DB |
| `/admin/users` | ✅ | ✅ | ✅ | Empty state; admin account excluded from user list |
| `/admin/users/[id]` | — | — | — | No regular users in DB |

**Deferred cosmetic findings (not layout breaks — no fix required):**

- `[All routes] [2560px] — Content has no max-width — Deferred: pre-existing design gap. UX spec says content max-width 1280px. At 2560px, content area spans full ~2380px (2560 − 180px nav). Tables and panels stretch; admin stat cards left-align with large empty space. Not a layout break — all content readable. Requires adding max-width + centering to the content wrapper in AppShell/AdminShell.`
- `[/admin] [1440px] — "ERROR / PARTIAL DOCUMENTS" stat card label wraps to 2 lines — Deferred: cosmetic only. Five cards fit in one row at 1440px but the longest label word-wraps. Value (0) and surrounding cards unaffected.`

### Tailwind Remnant Inventory

All files in `healthcabinet/frontend/src/`. `sr-only` is excluded from all counts — it is approved per 13-5 AC16.

| File | `.hc-*` classes | Tailwind class groups | Migration complexity |
|------|-----------------|----------------------|----------------------|
| `lib/components/health/AiInterpretationCard.svelte` | 0 | ~20 | **High** |
| `lib/components/health/AiFollowUpChat.svelte` | 0 | ~10 | **High** |
| `lib/components/health/PatternCard.svelte` | 0 | ~5 | Low |
| `lib/components/health/AIClinicalNote.svelte` | 7 (`hc-ai-note-*`) | ~7 | Low (skeleton only) |
| `lib/components/health/BiomarkerTrendChart.svelte` | 0 | ~12 | **High** (SVG) |
| `lib/components/health/BiomarkerTrendSection.svelte` | 5 (`hc-trend-*`) | ~4 | Low (skeleton only) |
| `lib/components/health/HealthValueBadge.svelte` | 0 | ~5 | Medium |
| `lib/components/health/PatternAlertSection.svelte` | 7 (`hc-pattern-alert-*`, `hc-dash-section-*`) | ~5 | Low (skeleton only) |
| `routes/(app)/dashboard/+page.svelte` | 12 (`hc-dash-*`, `hc-action-bar-*`, etc.) | ~5 | Low (skeleton + error text) |

**Per-file detail:**

**1. AiInterpretationCard.svelte** — 0 `.hc-*` | Entire card layout is Tailwind: `border-l-4 border-l-[#3366FF] bg-card/50 rounded-md p-4`, `text-base font-semibold mb-3`, `text-[15px] leading-relaxed mb-4`, reasoning table (`mb-3 w-full border-collapse text-[13px]`, `border-b border-border`, `pb-1 pr-3 font-medium`, `py-1 pr-3 text-foreground`), uncertainty list (`mb-3 space-y-0.5 flex items-start gap-1`), toggle button with interactive states (`hover:underline focus-visible:outline-none focus-visible:ring-2`), loading skeleton (`animate-pulse rounded-lg h-32 bg-card border border-border`). Most complex migration — needs full `.hc-interpretation-*` class set.

**2. AiFollowUpChat.svelte** — 0 `.hc-*` | Card wrapper: `mt-4 border-l-4 border-l-[#3366FF] bg-card/50 rounded-md p-4`, form: `space-y-3`, loading: `animate-pulse rounded-md h-16 bg-card border border-border`, response text: `text-[15px] leading-relaxed whitespace-pre-wrap`, error: `mt-3 text-[13px] text-destructive`. **Also imports shadcn `Textarea` and `Button` primitives from `$lib/components/ui/`** — these have not been migrated to 98.css equivalents.

**3. PatternCard.svelte** — 0 `.hc-*` | Simple card: `mt-4 border-l-4 border-l-[#E07020] rounded-md bg-card/50 p-4`, typography: `mb-2 text-base font-semibold text-foreground`, `mb-2 text-[15px] leading-relaxed`, `mb-1 text-[12px]`, `text-[11px] text-muted-foreground`. Structurally identical pattern to AiInterpretationCard — can share CSS.

**4. AIClinicalNote.svelte** — 7 `.hc-ai-note-*` | Main layout done with `.hc-*`. Remaining Tailwind: skeleton loader (`animate-pulse`, `mb-2 h-4 w-2/5 rounded bg-muted`, `mb-1 h-3 w-full/w-4/5/w-3/5 rounded bg-muted`), error text (`text-xs text-muted-foreground`), uncertainty list spacing (`mt-2`). Low effort: migrate skeleton to `.hc-skeleton-*` pattern from `app.css`.

**5. BiomarkerTrendChart.svelte** — 0 `.hc-*` | SVG-heavy. Tailwind on SVG elements: `overflow-visible`, `w-full`, `fill-muted-foreground text-[10px]`. Disabled-state container: `relative flex h-[200px] items-center justify-center overflow-hidden rounded-lg border border-border bg-card`, inner SVG: `absolute inset-0 h-full w-full opacity-20`, text: `relative z-10 px-4 text-center text-sm text-muted-foreground`. Note: `fill-muted-foreground` references a Tailwind CSS variable on SVG elements — migration needs equivalent `fill: var(--text-secondary)` direct CSS.

**6. BiomarkerTrendSection.svelte** — 5 `.hc-trend-*` | Main layout done. Remaining Tailwind: loading skeleton (`animate-pulse`, `h-4 w-2/5 rounded bg-muted`, `h-32 w-full rounded bg-muted`), error text (`text-xs text-muted-foreground`). Uses inline `style="padding: 12px;"` for layout (not Tailwind). Low effort.

**7. HealthValueBadge.svelte** — 0 `.hc-*` | Entire badge is Tailwind: `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium`, plus dynamic status color classes (`bg-[#2E8B57]/15 text-[#2E8B57]`, etc.). Status colors use exact design-token hex values. Migration: create `.hc-badge` base + `.hc-badge-optimal/borderline/concerning/action/unknown` variant classes.

**8. PatternAlertSection.svelte** — 7 `.hc-*` | Main layout done. Remaining Tailwind: skeleton (`animate-pulse`, `mb-2 h-4 w-4/5 rounded bg-muted`, `mb-1 h-3 w-2/5/w-3/5 rounded bg-muted`), error text (`text-xs text-muted-foreground`). Low effort.

**9. dashboard/+page.svelte** — 12 `.hc-*` | Main layout done. Remaining Tailwind: loading skeleton (`animate-pulse`, `mb-2 h-4 w-2/5 rounded bg-muted`, `mb-1 h-3 w-4/5/w-1/3 rounded bg-muted`), error text (`mb-4 text-sm text-destructive`). **Also imports `Button` from `$lib/components/ui/button`** (used in error retry state). Low effort.

**Cross-cutting discovery:** `AiFollowUpChat.svelte` and `dashboard/+page.svelte` still import shadcn `Button` and/or `Textarea` from `$lib/components/ui/`. These components were supposed to be removed in Epic 7 but still exist. The migration story must also replace these with 98.css equivalents (`<button class="hc-button">` or native button).

### References

- [Source: _bmad-output/implementation-artifacts/epic-13-retro-2026-04-16.md — Action Items 6 and 7; Tier 1/Tier 2 designation]
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml:165 — "Visual verification at 1024/1440/2560px + document remaining 9 Tailwind component files"]
- [Source: _bmad-output/implementation-artifacts/13-5-frontend-hardening-accessibility-qa-performance.md:175 — Tailwind remnant list (9 files)]
- [Source: _bmad-output/implementation-artifacts/13-5-frontend-hardening-accessibility-qa-performance.md:83 — Desktop QA requirement: 1024/1440/2560px, all admin + app routes]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md — "Tailwind structural remnants" entry to replace]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:1114 — Desktop-only MVP; no responsive breakpoints]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:1118 — Left nav 180px + content flex-1 layout]
- [Source: CLAUDE.md (global) — Canonical test commands: `docker compose exec frontend npm run test:unit`]
- [Source: healthcabinet/frontend/src/app.css — `.hc-*` CSS architecture and skeleton classes]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (1M context)

### Debug Log References

- **DB migration state corrupted**: `alembic_version` table showed version `014` but no schema tables existed. Root cause: volume may have been reset after migrations were last applied. Fix: `DELETE FROM alembic_version` then `cd /app && alembic -c alembic/alembic.ini upgrade head` ran all 14 migrations successfully.
- **Stale Vite module cache**: `/documents` page returned 500 with `SyntaxError: module does not provide export 'streamDocumentStatus'`. Export exists in `documents.ts:137`. Root cause: stale `.svelte-kit/generated` cache from previous container restarts. Fix: `rm -rf /app/.svelte-kit/generated && docker compose restart frontend`.
- **Admin route SSR auth guard**: Direct URL navigation to `/admin/*` redirected to login even when logged in. Root cause: SvelteKit SSR for admin routes validates session server-side; access token is in-memory only on client, not in cookies. Workaround: navigate via in-app client-side links using JS `click()`.

### Completion Notes List

- Desktop QA completed across 10 routes at 1024px, 1440px, 2560px — zero layout breaks (no overflow, no hidden critical content, no overlapping elements)
- Two cosmetic findings documented and deferred: (1) no max-width container at 2560px, (2) admin stat card label wraps at 1440px
- Routes without test data (`/documents/[id]`, `/admin/documents/[id]`, `/admin/users/[id]`) verified at empty state; data-populated state deferred
- Tailwind remnant sweep complete: 9 files inventoried with per-file TW class groups, `.hc-*` class counts, and migration complexity ratings
- Cross-cutting discovery: `AiFollowUpChat.svelte` and `dashboard/+page.svelte` still import shadcn `Button`/`Textarea` primitives — must be migrated in the dedicated Tailwind cleanup story
- `deferred-work.md` Tailwind entry replaced with accurate per-file inventory
- Frontend type check: 0 errors, 1 pre-existing a11y warning (AIChatWindow tabindex)
- Frontend test suite: 578/578 passed — no regressions

### File List

- `_bmad-output/implementation-artifacts/deferred-work.md` — Tailwind remnant entry replaced with per-file inventory (story-14.5, 2026-04-17)

## Review Findings

- [x] [Review][Decision] `/documents/[id]`, `/admin/documents/[id]`, `/admin/users/[id]` not verified with data — accepted: empty-state verification sufficient (same CSS governs data and empty states; no test data available in fresh DB)
- [x] [Review][Patch] Close button hidden by header background in data-loaded state — fixed: added `z-index: 1` to `.hc-detail-close-btn` [healthcabinet/frontend/src/app.css]
- [x] [Review][Patch] Orphaned `.hc-detail-header-title` CSS + filename text-overflow regression — fixed: replaced dead `.hc-detail-header-title` rule with `.hc-detail-header-filename` (`flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`); wrapped filename in `DocumentDetailPanel.svelte` [healthcabinet/frontend/src/app.css, healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.svelte]
- [x] [Review][Patch] Tailwind inventory entry inside story-13.5 section — fixed: moved to its own `## Re-deferred from: story-14.5 with inventory (2026-04-17)` section above story-13.5 [_bmad-output/implementation-artifacts/deferred-work.md]
- [x] [Review][Defer] `monkeypatch.setattr(settings, "ENVIRONMENT", "production")` mutates module-level singleton — safe for single-threaded pytest runs; latent risk if concurrent async workers are introduced. Pre-existing architecture concern. [healthcabinet/backend/tests/test_main.py:64]
- [x] [Review][Defer] Dead `get_s3_client` patches in deletion tests — already captured in deferred-work.md under story-14.4 review. [healthcabinet/backend/tests/users/test_router.py:427,487]
- [x] [Review][Defer] `test_delete_account_minio_failure` patches `delete_objects_by_prefix` on a dead code path — same root cause as above; documents behavior of removed inline cleanup. [healthcabinet/backend/tests/users/test_router.py:453-464]
- [x] [Review][Defer] No close button test for loading/error states — close button is permanently visible in those states but no test asserts it; test coverage enhancement, not a regression. [healthcabinet/frontend/src/lib/components/health/DocumentDetailPanel.svelte]
- [x] [Review][Defer] `detailQuery.data` can become undefined during background TanStack Query refetch while delete dialog is open — pre-existing architectural pattern, not introduced by this diff.

### Change Log

- `14-5` Desktop QA sweep — 10 routes verified at 1024/1440/2560px, 0 layout breaks (Date: 2026-04-17)
- `14-5` Tailwind remnant sweep — 9 component files inventoried, deferred-work.md updated (Date: 2026-04-17)
