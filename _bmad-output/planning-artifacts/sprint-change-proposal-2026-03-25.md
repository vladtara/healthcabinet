# Sprint Change Proposal

**Date:** 2026-03-25
**Project:** set-bmad / HealthCabinet
**Approved:** yes
**Scope Classification:** Moderate

## 1. Issue Summary

Implementation readiness review on 2026-03-25 found a planning-level scope contradiction across the active HealthCabinet artifacts. `prd.md`, `ux-design-specification.md`, and `architecture.md` still model billing, Stripe, and paid AI gating as active MVP behavior, while `epics.md` partially defers billing and removes some gating. The result is ambiguous implementation intent.

### Evidence

- `implementation-readiness-report-2026-03-25.md` verdict: `NOT READY`
- FR26-FR29 are still present as active product requirements in the PRD, but are deferred in practice
- architecture still contains Stripe and `require_paid_tier` assumptions
- epics contain numbering and traceability defects, including references to non-existent `Epic 7`

## 2. Impact Analysis

### Epic Impact

- Epic 4 must be normalized so AI features are not described as paid-gated.
- Billing must be removed from active MVP epic scope and treated as deferred work.
- Epic numbering and FR mapping need repair before further story execution.

### Story Impact

- Story references such as `2.6 -> 5.2` need correction.
- Any story text with paid-user, billing, or Stripe assumptions needs cleanup.
- Existing implementation artifacts should remain, but their planning references may need normalization.

### Artifact Conflicts

- PRD: MVP scope and FR classification need correction.
- Architecture: billing module, paid gating, and queue/access assumptions need correction.
- UX: remove upgrade CTAs, locked AI states, and paid-only branches from MVP.
- Sprint tracking: align active scope and deferred work with the updated plan.

### Technical Impact

- Prevents accidental Stripe or billing implementation.
- Simplifies MVP delivery path.
- Reduces ambiguity in route guards, backend module boundaries, and UI behavior.

## 3. Recommended Approach

**Selected approach:** Hybrid = Direct Adjustment + MVP Review

### Approved Decision

- Billing and Stripe are not implemented now.
- Billing moves fully to deferred Phase 2 scope.
- AI features remain in MVP without paid gating.

### Rationale

- This resolves the contradiction without rollback.
- The core MVP loop remains intact: onboarding, upload, extraction, dashboard, interpretation, trends.
- The change is mostly document and backlog normalization, not product redesign.

### Estimate

- Effort: Medium
- Risk: Low-Medium
- Timeline impact: short planning interruption now, lower execution risk later

## 4. Detailed Change Proposals

### PRD

**OLD**

- MVP includes billing and paid AI tier behavior.
- FR26-FR29 sit in the active requirement set.

**NEW**

- Billing/Stripe removed from MVP implementation scope.
- AI capabilities remain in MVP without tier gating.
- FR26-FR29 moved to explicit deferred Phase 2 scope.

**Justification**

Aligns product requirements with actual implementation intent.

### Architecture

**OLD**

- Stripe is an active MVP component.
- AI endpoints assume paid-tier gating.
- Queueing/access patterns distinguish free vs paid behavior.

**NEW**

- Remove Stripe and paid-tier gating from MVP architecture.
- Use a single MVP access path for AI capabilities.
- Mark billing as deferred design work, not current implementation.

**Justification**

Prevents technical design from pulling the team back into monetization work.

### UX

**OLD**

- Upgrade CTAs, locked AI states, paid-only paths, and free-to-paid conversion journeys are active in MVP UX.

**NEW**

- Remove active monetization flows from MVP UX.
- Make Q&A and pattern detection part of the normal MVP experience.
- Keep any monetization notes as future-state only.

**Justification**

Keeps UX aligned with the actual MVP and removes false interaction branches.

### Epics and Stories

**OLD**

- Epic numbering and FR mapping are inconsistent.
- Some stories still reference paid users, Stripe assumptions, or incorrect follow-on stories.

**NEW**

- Normalize epic numbering and FR traceability.
- Remove billing from active MVP epics.
- Fix stale story references and paid-gating wording.

**Justification**

Restores execution clarity for story implementation.

### Sprint Tracking

**OLD**

- Active/deferred scope separation is not fully canonical.

**NEW**

- Update `sprint-status.yaml` and `deferred-work.md` so billing/Stripe are explicitly deferred and no active sprint item implies monetization work.

**Justification**

Keeps sprint execution aligned with the corrected plan.

### Epic 3 UX Addendum

**OLD**

- Epic 3 starts directly with dashboard baseline and visualization work while the already-built registration and onboarding pages remain visually weak.

**NEW**

- Add a new first story in Epic 3: `Story 3.0: Registration & Onboarding UI Refinement`.
- This story applies the approved HealthCabinet UI/UX direction to `/register` and `/onboarding` before dashboard work begins.
- The story is explicitly visual/experience refinement only; it does not introduce billing, Stripe, or new business logic.

**Justification**

The first-run experience currently looks below product standard. Fixing it before Epic 3 dashboard work gives the product a more coherent foundation and avoids carrying visibly weak entry flows into later UX layers.

## 5. Implementation Handoff

**Scope classification:** Moderate

### Route To

- Product Owner / Scrum Master for backlog and artifact normalization
- Architect for architecture cleanup
- Development team only after planning artifacts are synchronized

### Responsibilities

- PO/SM: update epic structure, deferred scope, sprint tracking
- Architect: remove MVP billing assumptions and paid gating from architecture
- Product/UX: remove monetization behavior from MVP UX and PRD scope text
- Product/UX + Dev: execute Epic 3 registration/onboarding UI refinement before baseline dashboard stories
- Dev team: continue implementation only after corrected artifacts are in place

### Success Criteria

- No MVP artifact implies billing/Stripe implementation now
- No MVP artifact implies paid-gated AI behavior
- Epic numbering and FR traceability are internally consistent
- Sprint tracker and deferred-work list reflect the same scope decision
- Registration and onboarding are visually aligned with the intended HealthCabinet UX before Epic 3 dashboard delivery

## 6. Workflow Completion

- Issue addressed: planning artifacts misaligned on MVP scope, billing, and AI gating
- Change scope: Moderate
- Artifacts to modify: `prd.md`, `architecture.md`, `ux-design-specification.md`, `epics.md`, `sprint-status.yaml`, `deferred-work.md`
- Routed to: Product Owner / Scrum Master, Architect, then Development team
