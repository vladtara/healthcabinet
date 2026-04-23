---
initiative: frontend-redesign
status: approved
created: 2026-04-02
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/ux-page-specifications.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-25.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-03-25.md
  - _bmad-output/project-context.md
---

# HealthCabinet Frontend Redesign Initiative

## Purpose

HealthCabinet has substantial product functionality, but the frontend experience is uneven. The current codebase already covers registration, onboarding, dashboard data, upload, documents, settings, and admin operations, yet the interface quality is behind the approved UX direction.

This initiative creates a dedicated frontend redesign track without rewriting the existing MVP epic structure. It is intentionally separate from `epics.md` so active requirement traceability stays stable while UI and UX debt are addressed as a focused program.

## Problem Statement

The lag is not primarily feature absence. The lag is presentation, cohesion, and interaction quality:

- Register and onboarding are in comparatively good shape after Story 3.0.
- Dashboard logic exists, but the route still falls short of the intended "health intelligence" reveal moment.
- Documents and settings are functional, but they need stronger layout consistency, hierarchy, and trust polish.
- Admin functionality exists, but the admin surface still feels like a functional stub rather than a product-grade console.
- Public and authenticated surfaces do not yet feel like one unified system.

## Initiative Goals

1. Bring every major frontend route into the approved Windows 98 clinical workstation aesthetic (98.css + Tailwind CSS v4, DM Sans typography).
2. Redesign the high-value product moments first: dashboard, upload, document recovery, admin operations.
3. Standardize layout, spacing, states, and interaction patterns so the app feels coherent instead of page-by-page.
4. Implement the redesign in controlled slices, preserving current backend contracts whenever possible.
5. Use each epic as a shippable step with tests, accessibility checks, and desktop verification (1024px+).

## Non-Goals

- No billing, Stripe, or paywall work.
- No major backend domain redesign unless a frontend epic is blocked by a missing contract.
- No aesthetic drift away from the approved HealthCabinet UX direction.
- No "big bang" rewrite of the frontend.

## UX Guardrails

- Windows 98 clinical workstation aesthetic — 98.css for all UI chrome (beveled panels, sunken data regions, menu bar, toolbar, status bar). DM Sans typography.
- Cool gray palette with Arctic Blue accent and semantic health status colors (green/yellow/orange/red reserved exclusively for clinical data).
- Color is never the only status signal.
- Every important flow must define loading, empty, success, partial, and error states.
- Desktop-only MVP (1024px+). Mobile and tablet support deferred to post-MVP.
- Existing functionality should be reused and re-skinned before new abstractions are introduced.
- shadcn-svelte and bits-ui are removed and replaced by 98.css primitives + custom Svelte 5 components.

### 12 Custom Components (from UX spec v2)

AppShell, PatientSummaryBar, BiomarkerTable, SparklineBar, AIClinicalNote, AIChatWindow, ImportDialog, DocumentList, DocumentDetailPanel, OnboardingWizard, AdminErrorDetail, HealthStatusBadge

## Current-State Snapshot

### Stronger Current Areas

- `/register` and `/onboarding` already received meaningful UX refinement.
- Upload state handling, document processing status, and partial recovery patterns already exist.
- Documents, settings, dashboard, and admin each have working functional scaffolds.

### Highest-Gap Areas

- `/dashboard` needs a full information-hierarchy redesign.
- `/admin` needs a real admin shell and product-grade navigation/overview patterns.
- Shared shell behavior is inconsistent between user and admin experiences.
- Public/auth routes need tighter consistency with the rest of the product.
- Data-rights UX is not yet expressed as a coherent user-facing experience.

## Epic Structure

### FE Epic 1: Design System and Shared Frontend Foundation (98.css Migration)

**Outcome:** Replace shadcn-svelte with 98.css, establish DM Sans typography, and build the shared visual foundation so route-level redesign does not drift.

**Primary scope:**

- `healthcabinet/frontend/src/app.css`
- `healthcabinet/frontend/src/lib/components/ui/*`
- 98.css installation and integration with Tailwind CSS v4
- shared page chrome (window frames, toolbar, menu bar, status bar), cards, section headers, tables, drawers, empty/error/loading states

**Story candidates:**

1. Install 98.css, remove shadcn-svelte and bits-ui, set up DM Sans from Google Fonts, establish Windows 98 gray palette + health status color tokens in Tailwind
2. Build base layout components using 98.css chrome: window frames, raised/sunken panels, toolbar, status bar
3. Migrate existing UI primitives (Button, Input, Label, Checkbox, Textarea, Badge) from shadcn-svelte to 98.css equivalents
4. Reusable empty, loading, error, success, and warning state components using 98.css panels
5. Data-display primitives for metric cards, status rows, slide-over panels, and dense sortable tables (98.css sunken panels + Tailwind layout)

**Exit criteria:**

- shadcn-svelte and bits-ui fully removed from package.json
- 98.css provides all UI chrome; Tailwind handles layout and spacing
- Shared primitives can support dashboard, documents, settings, and admin without custom one-off styling
- The visual system is consistent across buttons, inputs, badges, cards, tables, and drawers
- All redesign epics can build on one foundation instead of inventing local patterns

**Why first:** Without this epic, every later route redesign will duplicate layout and state logic. The 98.css swap is the single largest dependency.

### FE Epic 2: Public and Authentication Surface Refresh

**Outcome:** Make the first impression trustworthy, polished, and visually aligned with the product.

**Primary scope:**

- `/`
- `/login`
- `/register`

**Story candidates:**

1. Landing page redesign with 98.css chrome, stronger hero, trust framing, and product narrative
2. Login page alignment with the register/onboarding visual standard using 98.css window frames
3. Final polish pass on register trust states, spacing, and 98.css consistency
4. Accessibility pass across all public/auth routes (desktop-only)

**Exit criteria:**

- Marketing and auth routes feel like the same product as the application shell
- Trust signals are explicit, useful, and visually deliberate
- Public/auth routes use 98.css chrome consistently

**Dependencies:** FE Epic 1

### FE Epic 3: Authenticated Shell and Navigation Architecture

**Outcome:** Unify the structure of logged-in experiences so every route inherits the same layout language.

**Primary scope:**

- `healthcabinet/frontend/src/routes/(app)/+layout.svelte`
- `healthcabinet/frontend/src/lib/components/AppShell.svelte`
- `healthcabinet/frontend/src/routes/(admin)/+layout.svelte`
- shared page headers, menu bar (File, View, Records, Tools, Help), icon toolbar, status bar

**Story candidates:**

1. AppShell redesign with 98.css window chrome: menu bar + toolbar + sunken content area + status bar. Left nav 180px. Desktop-only (1024px+).
2. Remove existing mobile bottom tab bar and tablet icon-rail responsive code
3. Admin shell variant with darker sidebar, admin-specific navigation, 98.css raised panels
4. Global feedback surfaces: route-level toasts, banners, and inline status regions using 98.css dialog/panel patterns

**Exit criteria:**

- User and admin experiences both sit inside coherent 98.css window-frame shells
- Navigation follows the Windows 98 menu bar + toolbar pattern on desktop
- Each major page can plug into a repeatable header/content/action layout

**Dependencies:** FE Epic 1

### FE Epic 4: Dashboard Redesign and Intelligence Reveal

**Outcome:** Turn `/dashboard` into the product's flagship experience.

**Primary scope:**

- `/dashboard`
- health summary cards
- biomarker presentation
- trend reveal
- AI interpretation blocks and reasoning placement

**Story candidates:**

1. Empty-state dashboard redesign: baseline narrative, first-upload CTA, blurred future-state preview in 98.css sunken panel
2. Active dashboard header and PatientSummaryBar with upload CTA, last-upload metadata, and counts
3. BiomarkerTable redesign (flagship component): dense sortable table with inline status indicators, reference ranges, SparklineBar, and expandable detail rows — 98.css sunken data region
4. Trend reveal experience for 2+ uploads, including stronger visual hierarchy for pattern alerts
5. AIClinicalNote and AIChatWindow integration below results table

**Exit criteria:**

- The dashboard communicates meaning before raw data
- BiomarkerTable is the flagship experience — dense, sortable, status-coded
- The route visibly delivers the "health intelligence" value proposition

**Dependencies:** FE Epics 1 and 3

### FE Epic 5: Documents Cabinet and Upload Workflow Redesign

**Outcome:** Make document handling feel precise, fast, and resilient instead of merely functional.

**Primary scope:**

- `/documents`
- `/documents/[id]`
- `/documents/upload`
- upload/retry/recovery components

**Story candidates:**

1. DocumentList redesign with 98.css file-explorer table pattern, clearer metadata hierarchy and status treatment
2. DocumentDetailPanel redesign as 98.css side panel for extracted values, recovery, and destructive actions
3. ImportDialog redesign with 98.css window chrome, drag-and-drop zone, and "Browse Files..." button
4. Processing pipeline with 98.css progress bar + 4 named stages (Uploading → Reading → Extracting → Generating)
5. Re-upload and partial-extraction flow polish so recovery feels guided rather than broken

**Exit criteria:**

- Documents and upload feel like one integrated workflow with 98.css chrome
- Partial and failed states are trustworthy and actionable
- ImportDialog uses retro-styled window frame

**Dependencies:** FE Epics 1 and 3

### FE Epic 6: Profile, Settings, and Data Rights Experience

**Outcome:** Turn settings from a utility form into a clear ownership and compliance surface.

**Primary scope:**

- `/settings`
- profile editing
- export/delete/consent UX
- related data-rights flows

**Story candidates:**

1. Medical profile page redesign with 98.css fieldsets, stronger sectioning and scanability
2. Consent history experience and timeline treatment in 98.css sunken panel
3. Data export UX with explicit status, delivery expectations, and success/failure messaging
4. Account and data deletion UX with calm but serious 98.css dialog confirmation flows
5. Unsaved-changes, save-success, and recovery patterns for profile editing

**Exit criteria:**

- Users clearly understand what profile data exists and how to control it
- GDPR-related actions feel trustworthy and product-grade
- Settings becomes a retention surface, not just an admin form

**Dependencies:** FE Epics 1 and 3

**Backend note:** This epic may depend on unfinished MVP backend/data-rights stories, but the UX and route structure should be designed first so backend follow-up has a clear target.

### FE Epic 7: Admin Experience Redesign and Frontend Hardening

**Outcome:** Elevate the admin surface from functional tooling to a focused operations console, then harden the frontend end-to-end.

**Primary scope:**

- `/admin`
- `/admin/documents`
- `/admin/documents/[document_id]`
- `/admin/users`
- `/admin/users/[user_id]`
- cross-app accessibility, regression, and performance validation

**Story candidates:**

1. Admin overview redesign with operational hierarchy and clear decision surfaces
2. Extraction error queue and manual correction UX refinement
3. User management and user-detail surface redesign
4. Admin shell/navigation consistency and route transitions
5. Final frontend hardening pass: accessibility audit, desktop QA (1024px–2560px), visual regression, and route-level performance fixes

**Story 5 — Carried-forward hardening debt (must land in 13-5):**

Scheduled via `epic-12-retro-2026-04-15.md` Action 3. These deferrals accumulated across Epics 11–12 and need an explicit absorption window before GA:

- **`HealthValueRow.svelte` Tailwind migration** — last Tailwind-styled component rendering inside 98.css panels (Epic 11 retro #2)
- **SSE `EventSource` token-as-query-param** — deferred 3× during Epic 11 as a security concern. Research fetch-based SSE or cookie-based auth for the processing-status stream (Epic 11 retro #3)
- **SSE auto-reconnect race / orphaned connections** — reliability issue flagged in Epic 11 reviews
- **Condition-chip disabled-state styling** — `.hc-profile-condition-chip` has no disabled visual state when rendered inside a disabled `<fieldset>`. A11y gap from Story 12-1
- **`previouslyFocused.focus()` guard** — slide-over and confirm-dialog both call `.focus()` on the stored trigger element without checking whether it's still attached or focusable. A11y robustness (Story 12-4 and epic-12-retro review defer)
- **Async destructive-action double-click guard** — component-level protection against firing `onConfirm` twice before `loading` is set by the parent. Pattern applies to ConfirmDialog and any future destructive-action component (Story 12-4 and epic-12-retro review defer)

**Exit criteria:**

- Admin can move through metrics, queue, corrections, and user-management flows without UI friction
- Admin pages match the product system while remaining operationally distinct
- The frontend redesign closes with measurable quality gates instead of aesthetic-only completion
- All six carried-forward hardening items above are resolved or explicitly re-deferred with a GA-waiver rationale

**Dependencies:** FE Epics 1 and 3, plus route-specific work from FE Epics 4 to 6 where shared patterns are reused

## Recommended Implementation Order

1. **FE Epic 1**: Lock the design system and state patterns first
2. **FE Epic 2**: Refresh public/auth so the first-run experience matches the future product standard
3. **FE Epic 3**: Standardize authenticated and admin shells before deeper page redesign
4. **FE Epic 4**: Redesign dashboard, the core user value moment
5. **FE Epic 5**: Redesign documents and upload, the operational heart of the product loop
6. **FE Epic 6**: Redesign settings and data-rights UX
7. **FE Epic 7**: Redesign admin and run final frontend hardening

## Delivery Method Per Epic

For each epic, use the same execution pattern:

1. Update route-level UX intent and acceptance criteria
2. Build or refine shared primitives only where reuse is proven
3. Implement one route slice at a time
4. Run route-level tests, desktop review (1024px–2560px), and accessibility verification
5. Close with a short design QA and regression pass before moving to the next epic

## Suggested First Three Stories

If execution starts immediately, begin with these:

1. **FE1.1**: Design token and shared state audit
2. **FE3.1**: App shell and admin shell alignment
3. **FE4.1**: Dashboard empty-state and active-header redesign

This sequence fixes the structural layer before touching the product's most important screen.

## Success Metrics for the Initiative

- Every primary route visually aligns with `ux-design-specification.md` and `ux-page-specifications.md`
- No page feels like an internal scaffold or placeholder
- Dashboard and admin are no longer the largest visual debt areas
- Desktop experience (1024px+) is polished and consistent across all routes
- Frontend regressions are caught by tests and QA gates during each epic, not after the redesign finishes

## Final Recommendation

Treat this as a **frontend modernization program**, not a cosmetic pass. The application already has enough functionality to justify a structured redesign. The right move is to upgrade the shared system first, then rebuild the highest-leverage user and admin surfaces in sequence.
