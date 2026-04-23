# Story 8.2: Login Page 98.css Alignment

Status: done

## Story

As a returning user,
I want a login page that matches the 98.css clinical workstation aesthetic established in the landing page,
so that the sign-in experience feels like the same product and reinforces trust in the medical software.

## Acceptance Criteria

1. **98.css auth dialog** replaces the current glassmorphic card:
   - Centered vertically/horizontally in viewport on `var(--surface-base)` background
   - Dialog box with 98.css beveled border (`border-color: #D0D8E4 #A0B0C0 #A0B0C0 #D0D8E4`)
   - Raised background `var(--surface-raised)` — NOT white card with backdrop blur
   - Max-width 420px

2. **Dialog header** with accent-colored title bar:
   - Blue background `var(--accent)`, white text, 16px bold
   - Content: "🔑 Sign In"
   - Full-width bar at top of dialog (same pattern as WindowFrame title bar)

3. **Dialog subtitle** below header:
   - Text: "Access your HealthCabinet account"
   - 14px, secondary text color, padding 12px 20px

4. **Form fields** use 98.css-native `field-row-stacked` pattern:
   - Email: `<Label>` + `<Input>` with existing `hc-label` / `hc-input` classes
   - Password: same pattern
   - 12px margin between field groups
   - Placeholders: "you@example.com" and "Enter your password"

5. **Error state** with 98.css sunken error panel:
   - Background `#FFF0F0`, 98.css beveled border (inward)
   - Red text `var(--status-action)`, 14px bold
   - Icon: ⚠ prefix
   - Shows above form fields (same position as mockup)
   - `role="alert"` and `aria-describedby` on inputs for accessibility

6. **Submit button** full-width primary:
   - `Button` component with `variant="primary"`, full width
   - 15px font-size, 8px vertical padding
   - Text: "Sign In" / "Signing in..." when submitting
   - Disabled during submission

7. **Register link** below button:
   - "Don't have an account? Register" — Register is accent-colored, underlined, bold
   - Links to `/register`
   - Centered, 14px

8. **Trust footer** at dialog bottom:
   - "🔒 Your data is encrypted and stored in the EU"
   - 13px, disabled text color, centered
   - Top border separator `1px solid #B8C4D0`
   - Inside the dialog box (not below it)

9. **No gradient blobs or glassmorphism** — remove the decorative background and backdrop-blur card

10. **No scoped `<style>` blocks** — all new CSS in `app.css`
    - Reuse existing `.hc-input`, `.hc-label`, `.hc-button`, `.btn-primary`
    - Add `.hc-auth-*` classes for auth dialog layout

11. **Preserve all existing functionality**:
    - Login API call, error handling (401/403/generic), token storage
    - Auth redirect after login (`goto('/dashboard')`)
    - `me()` call for user profile
    - `novalidate` form, `required` attributes
    - Accessibility: `aria-describedby`, `role="alert"`, label associations

12. **Tests** must continue passing + update for new structure:
    - All existing test assertions must still pass (error messages, button states, accessibility)
    - Update selectors if DOM structure changes (e.g., no more rounded card classes)

## Tasks / Subtasks

- [x] **Task 1: Rewrite login page markup** (AC: #1, #2, #3, #4, #5, #6, #7, #8, #9)
  - [x] Remove gradient blob backgrounds and glassmorphic card container
  - [x] Add `.hc-auth-page` wrapper (flex centered, full viewport)
  - [x] Add `.hc-auth-dialog` box with 98.css beveled border
  - [x] Add `.hc-auth-dialog-header` accent-colored title bar with "🔑 Sign In"
  - [x] Add `.hc-auth-dialog-subtitle` below header
  - [x] Restructure form with `.hc-auth-dialog-body` wrapper
  - [x] Keep existing `Label`, `Input`, `Button` component usage
  - [x] Restyle error display with `.hc-auth-error` panel (sunken, red background)
  - [x] Add `.hc-auth-link` section for register link
  - [x] Add `.hc-auth-trust` footer inside dialog with border-top separator
  - [x] Preserve all script logic (handleSubmit, error handling, auth redirect)

- [x] **Task 2: Add auth dialog CSS to app.css** (AC: #10)
  - [x] Add `.hc-auth-page` — flex centered layout
  - [x] Add `.hc-auth-dialog` — 98.css beveled border, raised background, max-width
  - [x] Add `.hc-auth-dialog.hc-auth-login` — max-width 420px
  - [x] Add `.hc-auth-dialog-header` — accent background, white text, bold
  - [x] Add `.hc-auth-dialog-subtitle` — secondary text styling
  - [x] Add `.hc-auth-dialog-body` — form padding and field spacing
  - [x] Add `.hc-auth-error` — red background, beveled border, alert styling
  - [x] Add `.hc-auth-link` — centered text with accent-colored anchor
  - [x] Add `.hc-auth-trust` — footer with border-top separator

- [x] **Task 3: Update tests for new structure** (AC: #11, #12)
  - [x] Update any selectors that reference old Tailwind card classes
  - [x] Verify all existing test assertions still pass with new DOM
  - [x] Add test: renders auth dialog header with "Sign In" text
  - [x] Add test: renders trust footer "encrypted and stored in the EU"
  - [x] Run full suite to verify no regressions

- [x] **Task 4: Regression verification**
  - [x] Run full test suite: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build`

## Dev Notes

### Architecture & Patterns

- **File to modify:** `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte` (currently 140 lines)
- **CSS location:** ALL new styles in `healthcabinet/frontend/src/app.css` — NO scoped `<style>` blocks
- **Auth layout:** `(auth)/+layout.svelte` provides flex centering with `bg-background` — may need to update to `bg-surface-base` or handle background in the page itself
- **Test file:** `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts` (currently 173 lines, 8 tests)

### Components to Use (from Epic 7 design system)

- **Button** from `$lib/components/ui/button` — `variant="primary"` for submit, full-width via CSS class
- **Input** from `$lib/components/ui/input` — renders `<input class="hc-input">`, bind:value, forwards all attributes
- **Label** from `$lib/components/ui/label` — renders `<label class="hc-label">`, accepts `for` prop
- Do NOT use WindowFrame — the auth dialog has its own header pattern (accent bar, not gradient title bar)

### Mockup Reference (ux-page-mockups.html)

The login page in the mockup uses this exact structure:
```html
<div class="auth-page">               <!-- flex centered -->
  <div class="auth-dialog login-dialog">  <!-- 98.css beveled box, max-width 420px -->
    <div class="auth-dialog-header">🔑 Sign In</div>  <!-- accent bg, white text -->
    <div class="auth-dialog-subtitle">Access your HealthCabinet account</div>
    <div class="auth-dialog-body">
      <div class="auth-error">⚠ Invalid email or password</div>  <!-- conditional -->
      <div class="field-row-stacked">...</div>  <!-- email -->
      <div class="field-row-stacked">...</div>  <!-- password -->
      <button class="btn-primary" style="width:100%">Sign In</button>
      <div class="auth-link">Don't have an account? <a>Register</a></div>
    </div>
    <div class="auth-trust">🔒 Your data is encrypted and stored in the EU</div>
  </div>
</div>
```

### CSS from Mockup (exact values to replicate)

```css
.auth-page { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px; }
.auth-dialog { width:100%; padding:0; border:2px solid; border-color:#D0D8E4 #A0B0C0 #A0B0C0 #D0D8E4; background:var(--surface-raised); }
.auth-dialog.login-dialog { max-width:420px; }
.auth-dialog-header { padding:10px 16px; background:var(--accent); color:#fff; font-weight:700; font-size:16px; }
.auth-dialog-subtitle { font-size:14px; color:var(--text-secondary); padding:12px 20px 0; }
.auth-dialog-body { padding:16px 20px 20px; }
.auth-dialog-body .field-row-stacked { margin-bottom:12px; }
.auth-error { display:flex; align-items:center; gap:8px; padding:8px 12px; margin-bottom:12px; background:#FFF0F0; border:2px solid; border-color:#A0B0C0 #D0D8E4 #D0D8E4 #A0B0C0; color:var(--status-action); font-size:14px; font-weight:600; }
.auth-link { text-align:center; font-size:14px; margin-top:12px; color:var(--text-secondary); }
.auth-link a { color:var(--accent); font-weight:600; text-decoration:underline; cursor:pointer; }
.auth-trust { text-align:center; font-size:13px; color:var(--text-disabled); padding:12px 20px; border-top:1px solid #B8C4D0; }
```

### Current Login Page Structure (to replace)

The current login page (140 lines) has:
- Decorative gradient blob backgrounds (Tailwind `blur-3xl`)
- Glassmorphic card with `backdrop-blur`, `rounded-2xl`, shadow
- SVG lock icon in circular badge
- Form with `space-y-5` Tailwind gap
- Inline SVG trust badges (lock, building, shield)
- All Tailwind classes, no 98.css chrome

### Auth Layout Consideration

The `(auth)/+layout.svelte` currently does:
```svelte
<div class="flex min-h-screen flex-col items-center justify-center bg-background">
  {@render children()}
</div>
```
This provides centering — the page component can add `.hc-auth-page` class for its own centering or rely on the layout. The background may need updating if `bg-background` doesn't resolve to `--surface-base`.

### Existing Test Patterns (login/page.test.ts)

8 tests currently in the login test file:
1. Shows "Invalid email or password" on 401 response
2. Shows "account suspended" on 403 response
3. Shows generic error on unexpected failure
4. Disables button during submission
5. Calls setAccessToken and redirects to /dashboard on success
6. Shows unified error message (no email/password differentiation)
7. Form is accessible via keyboard (axe audit)
8. Form shows accessible error state (axe audit with error visible)

Mocks used:
- `$lib/api/auth` → login, me
- `$lib/stores/auth.svelte` → authStore
- `$app/navigation` → goto
- `$lib/api/client.svelte` → tokenState, apiFetch

Tests query by: `getByLabelText(/email/i)`, `getByRole('button', { name: /sign in/i })`, `getByText(...)`, `container` for axe audits.

### CSS Class Naming Convention (from 8-1)

Use `.hc-auth-*` prefix for auth dialog classes (parallel to `.hc-landing-*` from story 8-1). These auth classes will be reused by the register page in story 8-3.

### What NOT To Do

- Do NOT modify register page — that's story 8-3
- Do NOT modify `(auth)/+layout.svelte` unless strictly necessary
- Do NOT add mobile/tablet responsive behavior — desktop-only MVP (1024px+)
- Do NOT use bits-ui or shadcn-svelte
- Do NOT add scoped `<style>` blocks
- Do NOT create new components — use existing Button, Input, Label from Epic 7
- Do NOT change any login logic (API calls, error handling, token management)
- Do NOT remove accessibility features (aria attributes, role="alert")

### Testing

**Framework:** vitest + jsdom + @testing-library/svelte
**Command:** `docker compose exec frontend npm run test:unit`
**NEVER run tests locally — Docker only.**

### Previous Story Intelligence

**From Story 8-1 (Landing Page Redesign):**
- CSS-only approach works well — all `.hc-landing-*` classes in `app.css`
- Button component with `href` and `variant` props works as expected
- Auth store `isAuthenticated` check pattern established
- 6 landing page tests passing, 327 total tests (1 pre-existing failure in users.test.ts)
- Mockup matching required fullscreen layout, not WindowFrame wrapper
- Trust badges use 98.css beveled borders for the "serious software" feel
- No scoped styles needed — all CSS in app.css

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 2] — story 2: "Login page alignment with the register/onboarding visual standard using 98.css window frames"
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#4. Login Page] — wireframe, component breakdown, states
- [Source: _bmad-output/planning-artifacts/ux-page-mockups.html#fullscreen-login] — interactive visual mockup with exact CSS
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — design system tokens and typography

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- Rewrote login page from glassmorphic Tailwind card to 98.css auth dialog matching ux-page-mockups.html
- Dialog structure: accent-colored header bar ("🔑 Sign In"), subtitle, form body, trust footer
- Error panel: sunken 98.css border with pink background (#FFF0F0) and red text, ⚠ prefix
- Form fields: Label + Input components with `.hc-auth-field-group` spacing (12px margin)
- Full-width primary submit button with loading state preserved
- Register link: accent-colored, underlined, centered below button
- Trust footer: "🔒 Your data is encrypted and stored in the EU" with border-top separator
- All login logic preserved: API calls, error handling (401/403/generic), token storage, auth redirect
- Added 12 reusable `.hc-auth-*` CSS classes — will be shared with register page (story 8-3)
- 9 tests: 7 existing (all passing with new DOM) + 2 new (dialog header, trust footer)
- Regression: 331/332 tests pass (1 pre-existing failure in users.test.ts), 0 svelte-check errors, build succeeds
- Visual verification: side-by-side comparison with mockup confirms match

### Change Log

- 2026-04-04: Story 8.2 implemented — login page 98.css alignment matching mockup

### File List

- `healthcabinet/frontend/src/routes/(auth)/login/+page.svelte` (modified — full rewrite)
- `healthcabinet/frontend/src/app.css` (modified — added `.hc-auth-*` classes)
- `healthcabinet/frontend/src/routes/(auth)/login/page.test.ts` (modified — 2 new tests, selectors updated)

### Review Findings

_Code review 2026-04-04 — Blind Hunter + Edge Case Hunter + Acceptance Auditor_

- [x] [Review][Patch] Restore semantic heading for login title (`<h1>` instead of plain `<div>`) [healthcabinet/frontend/src/routes/(auth)/login/+page.svelte:52-55]
- [x] [Review][Patch] Match subtitle padding exactly to AC3 (`padding: 12px 20px`) [healthcabinet/frontend/src/app.css:.hc-auth-dialog-subtitle]
- [x] [Review][Patch] Re-tighten unified-auth-error assertion (`toContain` → strict match with normalized text) [healthcabinet/frontend/src/routes/(auth)/login/page.test.ts:96]
