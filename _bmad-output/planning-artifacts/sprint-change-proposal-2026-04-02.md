# Sprint Change Proposal — 2026-04-02

## 98.css Design System Pivot & Epic Restructuring

**Date:** 2026-04-02
**Triggered by:** UX Design Specification v2 — Windows 98 clinical workstation aesthetic
**Prior proposal:** [sprint-change-proposal-2026-03-25.md](sprint-change-proposal-2026-03-25.md) (billing removal)
**Status:** Approved

---

## Section 1: Issue Summary

### Problem Statement

The UX Design Specification was significantly revised from v1 (Bloomberg/Stripe dark-neutral) to v2 (Windows 98 clinical workstation aesthetic). This introduces a fundamental visual direction change that conflicts with the current frontend implementation and planning artifacts:

1. **Component library swap:** shadcn-svelte + bits-ui → 98.css (~10KB CSS, framework-agnostic)
2. **Typography change:** Inter → DM Sans (Google Fonts CDN)
3. **Responsive strategy change:** Full responsive (375px–2560px) → Desktop-only MVP (1024px+)
4. **Visual language change:** Flat modern dark theme → Beveled panels, sunken data regions, menu bar, toolbar, status bar
5. **Component count expansion:** 5 shadcn-based primitives → 12 custom health-domain components

### Discovery Context

The UX spec v2 was approved with the 98.css direction, but planning artifacts (`frontend-redesign-epics.md`, `epics.md`, `project-context.md`, `architecture.md`, `CLAUDE.md`) still referenced the old design system. The `frontend-redesign-epics.md` (created 2026-04-02, draft status) contained 11 contradictions with the approved UX direction, including stating "Mobile is a first-class target" when the spec mandates desktop-only MVP.

### Evidence

- `ux-design-specification.md` lines 268–295: Explicit 98.css + Tailwind dual-layer system
- `ux-design-specification.md` line 1048: "Desktop only for MVP"
- `frontend-redesign-epics.md` line 54: "Mobile is a first-class target" (contradiction)
- `architecture.md` lines 166, 306, 353, 416, 541, 808, 845: All reference shadcn-svelte (stale)
- `project-context.md` line 24: References bits-ui (shadcn dependency, to be removed)

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 7 (old) | **Replaced** | 5 stories removed. Replaced by 7 new frontend redesign epics (Epics 7–13) |
| Epic 6 | **Partially deferred** | Story 6-1 (export) done. Stories 6-2 (deletion) and 6-3 (consent history) deferred until after Epics 7–13 |
| Epics 1–5 | No impact | Already completed |

### Story Impact

- **Old stories removed:** 7-1 through 7-5 (all assumed shadcn-svelte, responsive design)
- **New story candidates:** ~35 story candidates across 7 FE Epics (to be detailed via create-story workflow)
- **Deferred stories:** 6-2 (account deletion), 6-3 (consent history view)

### Artifact Conflicts Resolved

| Artifact | Conflicts Found | Changes Made |
|----------|----------------|--------------|
| `ux-design-specification.md` | Line 83 responsiveness contradiction | Updated to desktop-only MVP |
| `prd.md` | Responsive design section, mobile references | Updated to desktop-only MVP |
| `architecture.md` | 7 shadcn-svelte references | All replaced with 98.css |
| `frontend-redesign-epics.md` | 11 contradictions (mobile, no 98.css mention) | Full rewrite of UX guardrails, story candidates, exit criteria |
| `epics.md` | Epic 7 (5 stories) outdated | Replaced with Epics 7–13 summaries |
| `sprint-status.yaml` | Old Epic 7 entries | Replaced with Epics 7–13 backlog entries |
| `project-context.md` | shadcn-svelte, bits-ui references | Updated tech stack |
| `CLAUDE.md` | Theme, components, font, layout references | All updated for 98.css direction |
| `ux-page-specifications.md` | No desktop-only note | Added header note |

### Technical Impact

- **No backend changes required** — 98.css is purely frontend. API contracts, SSE events, Pydantic schemas unchanged.
- **Frontend dependency changes:** Remove `shadcn-svelte`, `bits-ui`. Add `98.css`. Add DM Sans from Google Fonts CDN.
- **No CSP header changes needed** — no existing Content-Security-Policy configuration found in backend.

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment

Modify the epic structure and planning artifacts to align with the approved UX v2 direction. No rollback of completed work required — Epics 1–5 are backend/feature work unaffected by the design system change. Story 6-1 (data export) is already done.

### Rationale

- **Effort:** Medium — all changes are to planning artifacts and documentation. No code changes in this proposal. Code changes happen in Epics 7–13 execution.
- **Risk:** Low — the frontend redesign preserves all backend contracts. The 98.css swap is additive (new CSS, remove old), not a logic rewrite.
- **Timeline impact:** Epics 7–13 are a larger scope than the old Epic 7 (7 epics vs 1 epic with 5 stories). However, the old Epic 7 stories would have needed similar scope once implementation began — the new structure is more honest about the work required.
- **Stories 6-2/6-3 deferral:** Acceptable. Data export (6-1) is the highest-priority GDPR feature. Deletion (6-2) and consent history (6-3) can be implemented after the frontend redesign without compliance risk.

### Trade-offs Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Direct Adjustment | **Selected** | Aligns artifacts with approved direction. No wasted work. |
| Rollback | Not viable | Nothing to roll back — Epics 1–5 are backend-heavy, unaffected |
| MVP Scope Reduction | Not needed | MVP features unchanged; only the visual layer is being redesigned |

---

## Section 4: Detailed Change Proposals

### 4.1 Epic Structure Changes

**REMOVED — Epic 7: Frontend Experience Foundation & Design System**
- Stories 7-1 through 7-5 (all assumed shadcn-svelte, responsive) → Deleted

**ADDED — Epics 7–13: Frontend Redesign Track (98.css Migration)**

| Epic | Name | Key Scope | Dependencies |
|------|------|-----------|--------------|
| 7 | Design System Foundation | 98.css install, shadcn removal, DM Sans, tokens, base layout | None |
| 8 | Public & Auth Surface | Landing, login, register with 98.css chrome | Epic 7 |
| 9 | Authenticated Shell & Navigation | AppShell, menu bar, toolbar, status bar, admin shell | Epic 7 |
| 10 | Dashboard Redesign | BiomarkerTable, PatientSummaryBar, AI panels | Epics 7, 9 |
| 11 | Documents & Upload | DocumentList, ImportDialog, processing pipeline | Epics 7, 9 |
| 12 | Settings & Data Rights | Profile, consent, export/delete UX | Epics 7, 9 |
| 13 | Admin & Hardening | Admin console, accessibility audit, QA | Epics 7, 9, 10–12 |

### 4.2 PRD Changes

**Section: Responsive Design**

OLD:
- Desktop-optimized; fully responsive from 375px (iPhone SE) to 2560px (wide desktop)
- Touch-friendly upload targets for mobile users photographing lab results

NEW:
- Desktop-only MVP (1024px+ to 2560px wide desktop). Mobile and tablet support deferred to post-MVP.
- Post-MVP: touch-friendly upload targets for mobile users photographing lab results

### 4.3 Architecture Changes

**Section: Frontend Architecture — Component library**

OLD: `shadcn-svelte | 1.1.1`
NEW: `98.css + custom Svelte 5 components | ~10KB`

**Section: Accessibility**

OLD: `shadcn-svelte accessible primitives; semantic HTML; color + text labels`
NEW: `98.css high-contrast chrome; semantic HTML required by design; color + text labels`

### 4.4 Sprint Status Changes

- Stories 6-2, 6-3: Added deferral comments
- Epic 7 entries: Replaced with Epics 7–13 (all backlog)
- Story stubs: Candidates only, to be created via create-story workflow

---

## Section 5: Implementation Handoff

### Change Scope: Moderate

This proposal modifies the epic structure, defers active stories, and introduces a new 7-epic frontend track. The artifact updates are complete. Implementation of the actual frontend code changes begins with Epic 7.

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **Scrum Master (Bob)** | Create first story for Epic 7 via create-story workflow. Update sprint plan. |
| **Developer (Amelia)** | Execute Epic 7 stories: install 98.css, remove shadcn-svelte, migrate primitives |
| **UX Designer (Sally)** | Review implementation against ux-design-specification.md and ux-page-mockups.html |

### Recommended Next Actions

1. **Immediate:** Run `bmad-create-story` for Epic 7, Story 1 (98.css foundation swap) — this is the critical-path blocker for all other FE epics
2. **After Epic 7 Story 1:** Create remaining Epic 7 stories, then proceed to Epic 8
3. **After Epics 7–13 complete:** Return to Stories 6-2 and 6-3

### Success Criteria

- All planning artifacts consistently reference 98.css, DM Sans, desktop-only MVP
- No stale shadcn-svelte, bits-ui, Inter, or mobile-responsive references remain
- Sprint status accurately reflects the new epic structure
- First story of Epic 7 is ready for development
