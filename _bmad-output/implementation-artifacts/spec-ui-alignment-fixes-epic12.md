---
title: 'UI alignment fixes: Medical Profile, Registration password reveal, Onboarding navbar'
type: 'bugfix'
created: '2026-04-05'
status: 'done'
baseline_commit: '37dd3c3'
context:
  - '_bmad-output/planning-artifacts/ux-design-directions-v2.html'
  - '_bmad-output/planning-artifacts/ux-page-mockups.html'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Three UI misalignments: (1) Medical Profile page doesn't match design-v2 — Basic Info fields stacked instead of inline, Sex uses radios instead of select, Health Conditions uses chips instead of checkbox grid, Family History uses textarea instead of checkbox grid. (2) Registration page has no password reveal toggle. (3) Onboarding shows full AppShell navbar/sidebar — mockups show fullscreen wizard with no navigation.

**Approach:** Restructure Medical Profile form layout to match design-v2 (inline fields, select dropdown, checkbox grids). Add password visibility toggle to registration inputs. Move onboarding to its own route group with an auth-guarded layout that renders no AppShell.

## Boundaries & Constraints

**Always:** Preserve all existing form validation, dirty-state tracking, and API contract. Use 98.css / design-system tokens. Keep all accessibility attributes (aria-labels, focus management).

**Ask First:** Changes to backend profile model or API contract. Adding new preset family history conditions beyond the 4 in design-v2.

**Never:** Change backend code. Remove consent history, data export, or account deletion sections. Break existing tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Password toggle click | User clicks eye icon on password field | Input type toggles between "password" and "text", icon updates | N/A |
| Family history checkboxes save | User checks "Heart Disease" + "Diabetes" | Saved as comma-joined string "Heart Disease, Diabetes" to existing `family_history` text field | N/A |
| Family history load with freetext | Profile has freetext `family_history` value that doesn't match presets | Show presets unchecked, display legacy value in a read-only note below checkboxes | N/A |
| Onboarding auth guard | Unauthenticated user navigates to /onboarding | Redirect to /login | N/A |

</frozen-after-approval>

## Code Map

- `src/routes/(app)/settings/+page.svelte` -- Medical Profile page: restructure Basic Info to inline, Sex to select, Conditions to checkbox grid, Family History to checkbox grid
- `src/app.css` -- Update `.hc-fieldset legend` color to `var(--accent)`, add checkbox-grid and inline-fields utility classes, add password-toggle styles
- `src/routes/(auth)/register/+page.svelte` -- Add password reveal toggle to both password fields
- `src/routes/(onboarding)/+layout.svelte` -- NEW: auth-guarded layout without AppShell (centered fullscreen)
- `src/routes/(onboarding)/+layout.ts` -- NEW: copy auth check from (app)/+layout.ts
- `src/routes/(onboarding)/onboarding/+page.svelte` -- MOVE from (app)/onboarding/

## Tasks & Acceptance

**Execution:**
- [x] `src/app.css` -- Add `.hc-profile-inline-fields` (flex row, gap 16px, wrap), `.hc-profile-checkbox-grid` (2-col grid, gap 10px 24px with checked highlight), `.hc-password-wrapper` (relative container for toggle icon), update `.hc-fieldset legend` color to `var(--accent)`
- [x] `src/routes/(app)/settings/+page.svelte` -- Restructure Basic Info into inline row (Age, Sex select, Height, Weight). Replace condition chips with checkbox grid. Replace Family History textarea with preset checkbox grid (Heart Disease, Diabetes, Thyroid Disease, Cancer) + legacy freetext display. Update state handling for family history as string array joined on save.
- [x] `src/routes/(auth)/register/+page.svelte` -- Add password visibility toggle button to Password and Confirm Password fields. Add `showPassword`/`showConfirmPassword` state. Toggle input type between "password"/"text".
- [x] `src/routes/(onboarding)/+layout.svelte` -- Create new route group with auth guard, QueryClientProvider, centered fullscreen layout (no AppShell)
- [x] `src/routes/(onboarding)/+layout.ts` -- Copy silent-refresh auth logic from `(app)/+layout.ts`
- [x] Move `src/routes/(app)/onboarding/+page.svelte` to `src/routes/(onboarding)/onboarding/+page.svelte`
- [x] Update existing tests if import paths changed

**Acceptance Criteria:**
- Given the Medical Profile page, when rendered, then Basic Info fields (Age, Sex, Height, Weight) appear in a single inline row with Sex as a `<select>` dropdown
- Given the Medical Profile page, when rendered, then Health Conditions shows a 2-column checkbox grid (not toggle chips)
- Given the Medical Profile page, when rendered, then Family History shows a 2-column checkbox grid with presets (Heart Disease, Diabetes, Thyroid Disease, Cancer)
- Given the registration page, when user clicks the eye icon on a password field, then the password text becomes visible and the icon changes
- Given the onboarding page at /onboarding, when rendered, then no header, sidebar, or status bar is visible — only the centered wizard dialog
- Given an unauthenticated user, when navigating to /onboarding, then they are redirected to /login

## Verification

**Commands:**
- `docker compose exec frontend npm run test:unit` -- expected: all tests pass
- `docker compose exec frontend npm run check` -- expected: no type errors

## Suggested Review Order

**Medical Profile restructure**

- Entry point: inline fields + select dropdown + checkbox grids replace old layout
  [`+page.svelte:377`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L377)

- Family history: case-insensitive preset matching with dedup, legacy text handling
  [`+page.svelte:163`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L163)

- Save handler joins family history checkboxes back to comma-separated string
  [`+page.svelte:268`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L268)

- Dirty tracking updated for family history array comparison
  [`+page.svelte:76`](../../healthcabinet/frontend/src/routes/(app)/settings/+page.svelte#L76)

**Password reveal toggle**

- Password + confirm fields wrapped with toggle buttons and dynamic SVG icons
  [`+page.svelte:125`](../../healthcabinet/frontend/src/routes/(auth)/register/+page.svelte#L125)

**Onboarding navbar removal**

- New auth-guarded layout without AppShell — centered fullscreen
  [`+layout.svelte:1`](../../healthcabinet/frontend/src/routes/(onboarding)/+layout.svelte#L1)

- Silent refresh auth logic (mirrors (app) layout)
  [`+layout.ts:1`](../../healthcabinet/frontend/src/routes/(onboarding)/+layout.ts#L1)

**Styling**

- Fieldset legend accent color, password toggle, inline-fields, checkbox-grid CSS
  [`app.css:338`](../../healthcabinet/frontend/src/app.css#L338)

**Tests**

- Settings page tests updated for checkbox grid, select dropdown, family history presets
  [`page.test.ts:83`](../../healthcabinet/frontend/src/routes/(app)/settings/page.test.ts#L83)
