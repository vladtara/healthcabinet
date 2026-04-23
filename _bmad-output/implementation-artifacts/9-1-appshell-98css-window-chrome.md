# Story 9.1: AppShell Redesign with 98.css Window Chrome

Status: done

## Story

As an authenticated user,
I want the application shell to use the 98.css clinical workstation aesthetic with a header bar, left navigation panel, sunken content area, and status bar,
so that the app feels like a professional medical desktop application consistent with the public pages.

## Acceptance Criteria

1. **App shell layout** — column flex, full viewport:
   - Header bar at top (40px)
   - Body area: left nav (200px) + content area (flex-1)
   - Status bar at bottom (24px)
   - All inside `.hc-app-shell` wrapper

2. **Header bar** (`.hc-app-header`):
   - Height: 40px, raised background `var(--surface-raised)`
   - Bottom border: 2px solid `#A0B0C0`, inset white shadow
   - Left: ⚕ icon (accent color) + "HealthCabinet" bold 16px
   - Right: user email (14px, secondary color) + "🚪 Sign Out" button (standard variant, 13px)
   - Sign Out calls `authStore.logout()` then `goto('/login')`

3. **Left navigation panel** (`.hc-app-left-nav`):
   - Width: 200px, min-width: 200px
   - Background: `var(--surface-sunken)` (white), 98.css sunken border
   - Nav header: "⚕ Navigation" — 13px bold, accent color, raised background with bottom border
   - Section labels: "APP PAGES" and "ADMIN" — 11px uppercase, disabled text color
   - Nav separators between sections: double 98.css etched line
   - Nav items: 14px, 10px 14px padding, 8px gap for icon+label, 3px left border (transparent/accent)
   - Active item: accent color text, bold, accent left border, `#F0F4FF` background
   - Hover: `#E8E8E8` background
   - `aria-current="page"` on active item

4. **Navigation items** (user routes):
   - 📊 Dashboard → `/dashboard`
   - 📁 Documents → `/documents`
   - 👤 Medical Profile → `/settings` (label matches mockup)
   - ⚙ Settings → `/settings` (if separate from profile — check current routes)
   - Admin section visible only if `authStore.user?.role === 'admin'`:
     - 🔧 Admin Console → `/admin`

5. **Content area** (`.hc-app-content`):
   - Flex-1, overflow-y auto
   - Background: `var(--surface-sunken)` (white), 98.css sunken border
   - Padding: 10px
   - Body wrapper has 4px padding and 4px gap between nav and content

6. **Status bar** at bottom:
   - Use existing `StatusBar` + `StatusBarField` components from Epic 7
   - Height: 24px, 13px font
   - Fields: page name (flex-1) + document count or status info + version
   - Apply `.hc-app-status-bar` class

7. **Remove responsive mobile/tablet layouts**:
   - Remove mobile bottom tab bar (<768px)
   - Remove tablet icon-only sidebar (768-1023px)
   - Desktop-only (1024px+) — single layout, no breakpoint switches
   - This is a separate story (9-2) but the new shell should NOT include them

8. **Preserve auth guard behavior**:
   - `(app)/+layout.ts` load function unchanged (tryRefresh, redirect)
   - `(app)/+layout.svelte` $effect auth check unchanged
   - Only render shell when `authStore.isAuthenticated`
   - QueryClientProvider wrapping unchanged

9. **No scoped `<style>` blocks** — all new CSS in `app.css`

10. **Use existing Epic 7 components**:
    - `Toolbar` from `$lib/components/ui/toolbar` — for toolbar row if needed
    - `StatusBar` + `StatusBarField` from `$lib/components/ui/status-bar`
    - `Button` from `$lib/components/ui/button` — for Sign Out and toolbar buttons

11. **Tests**:
    - Renders header with "HealthCabinet" brand
    - Renders left nav with Dashboard, Documents, Profile items
    - Renders status bar
    - Sign Out button calls logout
    - Admin nav section hidden for non-admin users

## Tasks / Subtasks

- [x] **Task 1: Rewrite AppShell.svelte** (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x] Remove mobile bottom tab bar markup
  - [x] Remove tablet icon-only sidebar markup
  - [x] Add `.hc-app-shell` wrapper (column flex, full viewport)
  - [x] Add `.hc-app-header` with brand + user area + Sign Out
  - [x] Add `.hc-app-body` wrapper (flex row, 4px padding/gap)
  - [x] Add `.hc-app-left-nav` with nav header, section labels, nav items, separators
  - [x] Add `.hc-app-content` area for page slot
  - [x] Add StatusBar with StatusBarField components at bottom
  - [x] Implement Sign Out handler calling `authStore.logout()` + `goto('/login')`
  - [x] Show admin nav section only if `authStore.user?.role === 'admin'`

- [x] **Task 2: Add app shell CSS to app.css** (AC: #9)
  - [x] Add `.hc-app-shell` — column flex, 100vh
  - [x] Add `.hc-app-header` — 40px, raised bg, border, shadow
  - [x] Add `.hc-app-header-brand` — flex, gap, bold
  - [x] Add `.hc-app-header-user` — flex, gap, secondary color
  - [x] Add `.hc-app-body` — flex row, flex-1, padding, gap
  - [x] Add `.hc-app-left-nav` — 200px, sunken border, white bg
  - [x] Add `.hc-app-nav-header` — raised bg, accent text, bold
  - [x] Add `.hc-app-nav-section-label` — uppercase, disabled color
  - [x] Add `.hc-app-nav-item` — flex, padding, border-left, hover
  - [x] Add `.hc-app-nav-item.active` — accent color, bold, blue bg
  - [x] Add `.hc-app-nav-separator` — etched double line
  - [x] Add `.hc-app-content` — flex-1, sunken border, padding, overflow
  - [x] Add `.hc-app-status-bar` — status bar overrides

- [x] **Task 3: Update (app)/+layout.svelte if needed** (AC: #8)
  - [x] Verify auth guard still works with new AppShell
  - [x] Verify QueryClientProvider wrapping unchanged

- [x] **Task 4: Write tests** (AC: #11)
  - [x] Create or update AppShell test file
  - [x] Test: renders header with HealthCabinet brand
  - [x] Test: renders nav items (Dashboard, Documents, Settings)
  - [x] Test: renders status bar
  - [x] Test: admin section hidden for regular users
  - [x] Run axe audit on shell

- [x] **Task 5: Regression verification**
  - [x] Run full test suite: `docker compose exec frontend npm run test:unit`
  - [x] Run `svelte-check`: zero new errors
  - [x] Run build: `docker compose exec frontend npm run build`

## Dev Notes

### Architecture & Patterns

- **File to modify:** `healthcabinet/frontend/src/lib/components/AppShell.svelte` (currently 155 lines, full rewrite)
- **Layout file:** `healthcabinet/frontend/src/routes/(app)/+layout.svelte` — wraps AppShell, has auth guard
- **CSS location:** ALL new styles in `healthcabinet/frontend/src/app.css`
- **No test file exists** for AppShell currently

### Components to Use (from Epic 7)

- **StatusBar** from `$lib/components/ui/status-bar` — container with `hc-status-bar` class, accepts children snippet
- **StatusBarField** from `$lib/components/ui/status-bar` — individual field wrapper
- **Button** from `$lib/components/ui/button` — for Sign Out button, `variant="standard"`
- **Toolbar** from `$lib/components/ui/toolbar` — optional, for toolbar row (if needed)

### Mockup Reference (ux-page-mockups.html)

App shell structure from mockup:
```html
<div class="app-shell">
  <!-- Header -->
  <div class="app-header">
    <div class="brand"><span class="icon">⚕</span> HealthCabinet</div>
    <div class="user-area">
      sofia.k@example.com
      <button class="signout-btn">🚪 Sign Out</button>
    </div>
  </div>
  <!-- Body -->
  <div class="app-body">
    <div class="left-nav">
      <div class="nav-header">⚕ Navigation</div>
      <div class="nav-section-label">App Pages</div>
      <div class="nav-item active">📊 Dashboard</div>
      <div class="nav-item">📁 Documents</div>
      <div class="nav-item">📂 Import Document</div>
      <div class="nav-item">👤 Medical Profile</div>
      <div class="nav-item">⚙ Settings</div>
      <div class="nav-separator"></div>
      <div class="nav-section-label">Admin</div>
      <div class="nav-item">🔧 Admin Console</div>
    </div>
    <div class="content-area">
      <!-- Page content -->
    </div>
  </div>
  <!-- Status Bar -->
  <div class="status-bar app-status-bar">
    <p class="status-bar-field">Page name</p>
    <p class="status-bar-field">12 Pages</p>
    <p class="status-bar-field">v2.0</p>
  </div>
</div>
```

### CSS from Mockup (exact values)

```css
.app-shell { display:flex; flex-direction:column; height:100vh; width:100vw; }
.app-header { display:flex; align-items:center; justify-content:space-between; height:40px; min-height:40px; padding:0 12px; background:var(--raised); border-bottom:2px solid #A0B0C0; box-shadow:inset 0 1px 0 #fff; }
.app-header .brand { font-weight:700; font-size:16px; display:flex; align-items:center; gap:4px; }
.app-header .brand .icon { color:var(--accent); font-size:18px; }
.app-header .user-area { display:flex; align-items:center; gap:10px; font-size:14px; color:var(--text-secondary); }
.app-body { flex:1; display:flex; overflow:hidden; padding:4px; gap:4px; }
.left-nav { width:200px; min-width:200px; overflow-y:auto; background:var(--sunken-bg); border:2px solid; border-color:#A0B0C0 #D0D8E4 #D0D8E4 #A0B0C0; padding:0; display:flex; flex-direction:column; }
.nav-header { display:flex; align-items:center; gap:6px; padding:6px 14px; background:var(--raised); border-bottom:2px solid #A0B0C0; box-shadow:inset 0 1px 0 #fff; font-size:13px; font-weight:700; color:var(--accent); letter-spacing:0.3px; }
.nav-item { display:flex; align-items:center; padding:10px 14px; cursor:pointer; font-size:14px; gap:8px; white-space:nowrap; border-left:3px solid transparent; }
.nav-item:hover { background:#E8E8E8; }
.nav-item.active { background:#F0F4FF; color:var(--accent); font-weight:700; border-left-color:var(--accent); }
.nav-separator { height:0; border-top:1px solid #A0B0C0; border-bottom:1px solid #D0D8E4; margin:6px 12px; }
.nav-section-label { font-size:11px; font-weight:700; color:var(--text-disabled); text-transform:uppercase; letter-spacing:0.8px; padding:8px 14px 2px; }
.content-area { flex:1; overflow-y:auto; overflow-x:hidden; background:var(--sunken-bg); border:2px solid; border-color:#A0B0C0 #D0D8E4 #D0D8E4 #A0B0C0; padding:10px; }
.app-status-bar { min-height:24px; padding:0; }
.app-status-bar .status-bar-field { font-size:13px; padding:2px 8px; }
.app-status-bar .status-bar-field:first-child { flex:1; }
```

### Current AppShell Structure (to replace)

The current AppShell (155 lines) has:
- 3-tier responsive layout: desktop sidebar (240px), tablet icon-only (56px), mobile bottom nav
- Tailwind-only styling, no 98.css chrome
- Navigation items: Dashboard, Documents, Profile (only 3 items)
- User email in desktop sidebar footer
- `$page` store for active detection
- `aria-current="page"` on active links

### Navigation Items (from mockup)

The mockup shows these nav items under "APP PAGES":
- 📊 Dashboard → `/dashboard`
- 📁 Documents → `/documents`
- 📂 Import Document → `/documents/upload`
- 👤 Medical Profile → `/settings` (maps to profile/settings page)
- ⚙ Settings → `/settings`

Note: "Import Document" and "Medical Profile" vs "Settings" may be consolidated. Check what routes actually exist. The current AppShell only has 3 items. The mockup has 5 + admin.

### Auth Store Access

```typescript
import { authStore } from '$lib/stores/auth.svelte';
// User data:
authStore.user?.email    // string
authStore.user?.role     // 'user' | 'admin'
authStore.isAuthenticated // boolean (derived)
authStore.logout()       // async, clears token + calls API
```

### Active State Detection (from current AppShell)

```typescript
import { page } from '$app/stores';
function isActive(href: string): boolean {
  return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
}
```

### What NOT To Do

- Do NOT modify `(app)/+layout.ts` — auth guard stays as-is
- Do NOT modify `(app)/+layout.svelte` beyond minimal changes to accommodate new shell
- Do NOT modify any page components — they plug into the content area as-is
- Do NOT add mobile/tablet responsive layouts — desktop-only MVP
- Do NOT add scoped `<style>` blocks
- Do NOT add keyboard shortcuts (Ctrl+I etc.) — that's post-MVP
- Do NOT add menu bar (File, View, etc.) — that may be a separate enhancement

### Testing

**Framework:** vitest + jsdom + @testing-library/svelte + axe-core
**Command:** `docker compose exec frontend npm run test:unit`
**NEVER run tests locally — Docker only.**

### Previous Story Intelligence

**From Epic 8 (stories 8-1 through 8-4):**
- CSS class naming: `.hc-[section]-[element]` prefix pattern works well
- All CSS in app.css — no scoped styles
- 98.css beveled borders: `border-color: #D0D8E4 #A0B0C0 #A0B0C0 #D0D8E4` (raised), reverse for sunken
- Raised background: `var(--surface-raised)`, sunken: `var(--surface-sunken)`
- Accent header bars work well for section identification
- Trust in existing Epic 7 components (Button, StatusBar, Toolbar)
- 334 total tests passing (1 pre-existing failure in users.test.ts)

### References

- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE Epic 3] — story 1: "AppShell redesign with 98.css window chrome"
- [Source: _bmad-output/planning-artifacts/ux-page-mockups.html#app-shell] — interactive mockup with exact CSS
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — design system, navigation patterns
- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md] — component breakdown

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Vite cache issue caused false compile error on first test run — cleared cache, resolved

### Completion Notes List

- Full rewrite of AppShell.svelte from responsive Tailwind sidebar to 98.css window chrome layout
- Header bar (40px): ⚕ brand icon + "HealthCabinet" text (left), user email + Sign Out button (right)
- Left nav (200px): sunken panel with "⚕ Navigation" header, "APP PAGES" section label, 3 nav items (Dashboard, Documents, Settings)
- Admin section: conditional on `authStore.user?.role === 'admin'`, shows "Admin Console" link
- Active nav item: accent blue text, bold, blue left border, `#F0F4FF` background
- Content area: flex-1 sunken panel with 10px padding, overflow scroll
- Status bar: uses StatusBar + StatusBarField from Epic 7, shows active page name + tier + version
- Sign Out: calls `authStore.logout()` then `goto('/login')`
- Removed all mobile bottom tab bar and tablet icon-only sidebar markup (desktop-only MVP)
- 20+ new `.hc-app-*` CSS classes matching mockup exactly
- 7 tests: header brand, nav items, status bar, user email, admin hidden, sign out button, axe audit
- Layout file unchanged — auth guard and QueryClientProvider intact
- Regression: 341/342 tests pass (1 pre-existing failure in users.test.ts), 0 svelte-check errors, build succeeds

### Change Log

- 2026-04-04: Story 9.1 implemented — AppShell 98.css window chrome redesign

### File List

- `healthcabinet/frontend/src/lib/components/AppShell.svelte` (modified — full rewrite, 155→97 lines)
- `healthcabinet/frontend/src/app.css` (modified — added `.hc-app-*` classes)
- `healthcabinet/frontend/src/lib/components/AppShell.test.ts` (new — 7 tests)

### Review Findings

_Code review 2026-04-04 — Blind Hunter + Edge Case Hunter + Acceptance Auditor_

- [x] [Review][Decision] D1: AC4 "Medical Profile" + "Settings" — kept as single "Settings" item since both map to `/settings` route. User decision: option 2.
- [x] [Review][Patch] P1: Added skip-to-content link with `.hc-skip-link` CSS (WCAG 2.4.1) [AppShell.svelte, app.css]
- [x] [Review][Patch] P2: `width: 100vw` → `width: 100%` to prevent horizontal overflow [app.css:.hc-app-shell]
- [x] [Review][Patch] P3: Added try/catch on `authStore.logout()` in handleSignOut [AppShell.svelte]
- [x] [Review][Defer] D2: No test for sign-out click flow — test coverage improvement
- [x] [Review][Defer] D3: No test for admin=true positive case — test coverage gap
- [x] [Review][Defer] D4: Hardcoded border colors in `.hc-app-*` — matches mockup, pre-existing pattern
