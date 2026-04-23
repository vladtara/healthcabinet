# Story 8.3: Register Page 98.css Consistency

Status: done

## Story

As a new user creating an account,
I want the registration page to match the 98.css clinical workstation aesthetic established in the login page,
so that the onboarding experience feels consistent and trustworthy.

## Acceptance Criteria

1. **98.css auth dialog** replaces the current glassmorphic card:
   - Reuse `.hc-auth-page`, `.hc-auth-dialog` classes from story 8-2
   - Apply `.hc-auth-register` modifier (max-width 460px)
   - Raised background `var(--surface-raised)`, beveled 98.css border

2. **Dialog header** with accent-colored title bar:
   - Content: "📝 Create Your Account"
   - Same `.hc-auth-dialog-header` class as login

3. **Dialog subtitle** below header:
   - Text: "Securely store, understand, and track your health data"
   - Reuse `.hc-auth-dialog-subtitle`

4. **Form fields** use `.hc-auth-field-group` spacing:
   - Email address: Label + Input (placeholder "you@example.com")
   - Password: Label + Input (placeholder "Choose a password") + helper text "Minimum 8 characters"
   - Confirm Password: Label + Input (placeholder "Repeat your password")
   - 12px margin between field groups
   - Inline field-level errors below inputs (emailError, passwordError)

5. **Helper text** below password field:
   - "Minimum 8 characters" in 13px, disabled text color
   - Add `.hc-auth-helper-text` class

6. **GDPR consent section** with 98.css styling:
   - Border-top separator (1px solid #B8C4D0), padding-top 12px
   - Checkbox + label "I consent to health data processing" (14px, bold)
   - Description text: "Your data is encrypted with AES-256 and stored exclusively in EU data centers. You can export or delete all data at any time."
   - Privacy Policy link in accent color, underlined
   - Add `.hc-auth-gdpr-section`, `.hc-auth-consent-row`, `.hc-auth-consent-label`, `.hc-auth-consent-desc`, `.hc-auth-consent-link` classes

7. **Submit button** full-width primary:
   - Text: "Create Account" / "Creating account..." when submitting
   - Disabled when consent unchecked OR during submission
   - Reuse `.hc-auth-submit` class from login

8. **Sign-in link** below button:
   - "Already have an account? Sign in" — Sign in is accent-colored, underlined
   - Reuse `.hc-auth-link` class from login

9. **Trust badges** below dialog (outside the dialog box):
   - 3 badges: "🔒 AES-256", "🇪🇺 EU Data", "🛡️ GDPR"
   - Reuse `.hc-landing-trust-badge` styling, 16px margin-top from dialog

10. **No gradient blobs or glassmorphism** — remove decorative background and backdrop-blur

11. **No scoped `<style>` blocks** — all new CSS in `app.css`

12. **Preserve all existing functionality**:
    - Registration API call, error handling (409/generic), token storage
    - Client-side validation (email blur, password blur/submit, confirm match)
    - GDPR consent gate, privacy policy version
    - Redirect to `/onboarding` after registration
    - Accessibility: aria-describedby, role="alert", label associations

13. **Tests** must continue passing + update for new structure

## Tasks / Subtasks

- [x] **Task 1: Rewrite register page markup** (AC: #1–#10, #12)
  - [x] Remove gradient blob backgrounds and glassmorphic card
  - [x] Wrap in `.hc-auth-page` > `.hc-auth-dialog.hc-auth-register`
  - [x] Add `.hc-auth-dialog-header` with "📝 Create Your Account"
  - [x] Add `.hc-auth-dialog-subtitle`
  - [x] Restructure form fields with `.hc-auth-field-group` and `.hc-auth-dialog-body`
  - [x] Add helper text below password field
  - [x] Restyle GDPR section with `.hc-auth-gdpr-section` classes
  - [x] Restyle form error with `.hc-auth-error` (if applicable)
  - [x] Add `.hc-auth-link` for sign-in link
  - [x] Add trust badges below dialog using `.hc-landing-trust-badge`
  - [x] Preserve all script logic (validation, submit, error handling)

- [x] **Task 2: Add register-specific CSS to app.css** (AC: #5, #6, #11)
  - [x] Add `.hc-auth-helper-text` — 13px, disabled text color
  - [x] Add `.hc-auth-gdpr-section` — border-top, padding-top, margin
  - [x] Add `.hc-auth-consent-row` — flex, align-items start, gap
  - [x] Add `.hc-auth-consent-label` — 14px, bold
  - [x] Add `.hc-auth-consent-desc` — 13px, secondary color, line-height
  - [x] Add `.hc-auth-consent-link` — accent color, underlined, bold
  - [x] Add `.hc-auth-trust-below` — trust badges wrapper below dialog

- [x] **Task 3: Update tests for new structure** (AC: #13)
  - [x] Update selectors that reference old Tailwind card classes
  - [x] Verify all 7 existing tests pass with new DOM
  - [x] Add test: renders auth dialog header with "Create Your Account"
  - [x] Add test: renders trust badges below dialog
  - [x] Run full suite to verify no regressions

- [x] **Task 4: Regression verification**
  - [x] Run full test suite: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build`

## Dev Notes

### Architecture & Patterns

- **File to modify:** `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte` (currently 217 lines)
- **CSS location:** ALL new styles in `healthcabinet/frontend/src/app.css` — NO scoped `<style>` blocks
- **Test file:** `healthcabinet/frontend/src/routes/(auth)/register/page.test.ts` (currently 66 lines, 7 tests)

### Components to Use

- **Button** from `$lib/components/ui/button` — `variant="primary"`, disabled logic
- **Input** from `$lib/components/ui/input` — renders `<input class="hc-input">`
- **Label** from `$lib/components/ui/label` — renders `<label class="hc-label">`
- **Checkbox** from `$lib/components/ui/checkbox` — renders `<input class="hc-checkbox">`

### Reusable CSS from Story 8-2 (login)

These classes already exist in `app.css` and MUST be reused:
- `.hc-auth-page` — flex centered layout
- `.hc-auth-dialog` — 98.css beveled border, raised background
- `.hc-auth-register` — max-width 460px (already defined)
- `.hc-auth-dialog-header` — accent bar, white text, bold
- `.hc-auth-dialog-subtitle` — secondary text, padding
- `.hc-auth-dialog-body` — form padding
- `.hc-auth-field-group` — 12px margin-bottom
- `.hc-auth-submit` — full-width button styling
- `.hc-auth-link` — centered text with accent anchor
- `.hc-auth-error` — sunken error panel (for formError)

### Mockup Reference (ux-page-mockups.html)

Register page structure from mockup:
```html
<div class="auth-page">
  <div class="auth-dialog register-dialog">  <!-- max-width 460px -->
    <div class="auth-dialog-header">📝 Create Your Account</div>
    <div class="auth-dialog-subtitle">Securely store, understand, and track your health data</div>
    <div class="auth-dialog-body">
      <div class="field-row-stacked">Email + input</div>
      <div class="field-row-stacked">Password + input + helper-text</div>
      <div class="field-row-stacked">Confirm Password + input</div>
      <div class="gdpr-section">
        <div class="consent-row">checkbox + label + desc + link</div>
      </div>
      <button class="btn-primary" full-width>Create Account</button>
      <div class="auth-link">Already have an account? Sign in</div>
    </div>
  </div>
  <div class="trust-signals">3 trust badges below dialog</div>
</div>
```

### CSS from Mockup (register-specific values)

```css
.helper-text { font-size:13px; color:var(--text-disabled); margin-top:2px; }
.gdpr-section { border-top:1px solid #B8C4D0; padding-top:12px; margin-top:4px; margin-bottom:16px; }
.consent-row { display:flex; align-items:flex-start; gap:8px; margin-bottom:8px; }
.consent-row input[type="checkbox"] { margin-top:3px; }
.consent-label { font-size:14px; font-weight:600; }
.consent-desc { font-size:13px; color:var(--text-secondary); line-height:1.6; margin-top:4px; }
.consent-link { color:var(--accent); font-weight:600; text-decoration:underline; cursor:pointer; }
```

### Key Differences from Login (story 8-2)

- Max-width: 460px (login = 420px)
- Header: "📝 Create Your Account" (login = "🔑 Sign In")
- Additional fields: confirm password
- Helper text below password field
- GDPR consent section with checkbox + description + privacy policy link
- Button disabled when consent unchecked (login has no consent gate)
- Field-level errors (emailError, passwordError) in addition to formError
- Trust badges below dialog (login has trust footer inside dialog)
- No trust footer inside dialog (login has `.hc-auth-trust`)
- Redirect to `/onboarding` (login redirects to `/dashboard`)

### What NOT To Do

- Do NOT modify login page — that's story 8-2 (done)
- Do NOT modify `(auth)/+layout.svelte`
- Do NOT add mobile/tablet responsive behavior
- Do NOT add scoped `<style>` blocks
- Do NOT create new components
- Do NOT change any registration logic (API, validation, consent, redirect)
- Do NOT remove accessibility features

### Testing

**Framework:** vitest + jsdom + @testing-library/svelte
**Command:** `docker compose exec frontend npm run test:unit`
**NEVER run tests locally — Docker only.**

### Previous Story Intelligence

**From Story 8-2 (Login Page 98.css):**
- `.hc-auth-*` CSS classes work well and are reusable
- Dialog header uses `<h1>` tag for semantics
- Error panel uses `.hc-auth-error` with ⚠ prefix and `aria-hidden` on icon
- Form error assertion needs text normalization for ⚠ prefix
- Auth layout provides centering — `.hc-auth-page` adds its own flex centering
- 331 total tests passing, 1 pre-existing failure in users.test.ts
- Subtitle padding is `12px 20px` (no bottom padding `0`)

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 2] — story 3: "Final polish pass on register trust states, spacing, and 98.css consistency"
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#5. Register Page] — wireframe, component breakdown
- [Source: _bmad-output/planning-artifacts/ux-page-mockups.html#fullscreen-register] — interactive visual mockup with exact CSS
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — design system tokens

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Rewrote register page from glassmorphic Tailwind card to 98.css auth dialog matching mockup
- Reused all `.hc-auth-*` CSS from story 8-2: dialog, header, subtitle, body, field-group, submit, link, error
- Added register-specific CSS: helper text, GDPR consent section (row, label, desc, link), trust-below wrapper
- Dialog header "📝 Create Your Account" with accent bar, subtitle, 460px max-width
- GDPR section: checkbox + label + description + privacy policy link with border-top separator
- Field-level errors use new `.hc-auth-field-error` class (13px, action red)
- Trust badges below dialog using `.hc-landing-trust-badge` from landing page
- All validation/registration logic preserved: email blur, password blur/submit, confirm match, consent gate, 409 handling
- 9 tests: 6 existing (all pass with new DOM) + 3 new (dialog header, subtitle, trust badges) — axe audit was #7 originally
- Regression: 333/334 tests pass (1 pre-existing failure in users.test.ts), 0 svelte-check errors, build succeeds
- Visual verification: side-by-side comparison with mockup confirms match

### Change Log

- 2026-04-04: Story 8.3 implemented — register page 98.css consistency matching mockup

### File List

- `healthcabinet/frontend/src/routes/(auth)/register/+page.svelte` (modified — full rewrite)
- `healthcabinet/frontend/src/app.css` (modified — added register-specific `.hc-auth-*` classes)
- `healthcabinet/frontend/src/routes/(auth)/register/page.test.ts` (modified — 2 new tests, structure updated)

### Review Findings

_Code review 2026-04-04 — Blind Hunter + Edge Case Hunter + Acceptance Auditor_

- [x] [Review][Patch] P1: Password helper text needs `id` + `aria-describedby` linkage for screen readers [register/+page.svelte:117-128, app.css]
- [x] [Review][Patch] P2: Consent label font-weight 600 → 700 to match spec "bold" [app.css:.hc-auth-consent-label]
- [x] [Review][Defer] D1: Hardcoded `#B8C4D0` in `.hc-auth-gdpr-section` border — matches mockup, pre-existing pattern
- [x] [Review][Defer] D2: `/privacy-policy` route may not exist — pre-existing, not introduced by this diff
- [x] [Review][Defer] D3: No test for "Passwords do not match" error path — pre-existing gap
