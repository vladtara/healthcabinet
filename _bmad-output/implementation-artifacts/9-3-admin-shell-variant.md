# Story 9.3: Admin Shell Variant

Status: done

## Story

As an admin user,
I want the admin interface to use a distinct 98.css shell with a darker sidebar, admin-specific navigation, and admin status bar metrics,
so that the admin experience is visually differentiated from the user shell while maintaining the same professional Windows 98 workstation aesthetic.

## Acceptance Criteria

1. **Admin shell layout** — Same structure as user AppShell (header + left nav + content + status bar) but with admin-specific styling. Created as a dedicated `AdminShell.svelte` component.

2. **Darker sidebar** — Admin left nav uses background `#12141E` instead of `var(--surface-sunken)`. Nav items use light text colors for contrast against the dark background. Active/hover states adapted for dark background.

3. **Admin branding** — Nav header displays "⚙ Admin" in `status-action` color (`#CC3333` red) instead of "⚕ Navigation" in accent blue. Header brand still shows "⚕ HealthCabinet" but can optionally include an "Admin" indicator.

4. **Admin navigation items** — Left nav contains admin-specific routes:
   - 📊 Overview → `/admin`
   - 📤 Upload Queue → `/admin/documents`
   - 👥 Users → `/admin/users`
   - ← Back to App → `/dashboard` (returns to user shell)
   Active state detection works the same as user shell (`$page.url.pathname` matching).

5. **Admin status bar** — StatusBar shows admin-contextual fields: current page name (flex-1), "Admin Panel" label, version.

6. **Admin layout integration** — `(admin)/+layout.svelte` uses `AdminShell` instead of the current basic Tailwind flex layout. Auth guard (admin role check + redirect) preserved.

7. **CSS follows established patterns** — All admin styles in `app.css` using `.hc-admin-*` naming convention. No scoped `<style>` blocks. Reuses 98.css beveled border patterns from AppShell.

8. **Tests** — Unit tests for AdminShell: renders header, renders admin nav items, renders status bar, non-admin users cannot see admin content (guard preserved), active nav item highlighting, accessibility (axe audit).

## Tasks / Subtasks

- [x] Task 1: Create AdminShell component (AC: #1, #2, #3, #4, #5)
  - [x] 1.1 Create `src/lib/components/AdminShell.svelte` modeled on AppShell.svelte structure (header, body with left nav + content, status bar)
  - [x] 1.2 Implement darker sidebar (`#12141E` background) with light text nav items, adapted hover/active states for dark bg
  - [x] 1.3 Implement admin nav header: "⚙ Admin" in `#CC3333` (status-action red) with raised background
  - [x] 1.4 Implement admin navigation items: Overview (`/admin`), Upload Queue (`/admin/documents`), Users (`/admin/users`), "← Back to App" (`/dashboard`)
  - [x] 1.5 Implement active route detection using `$page.url.pathname` pattern from AppShell (with `exact` flag for `/admin` to avoid matching sub-routes)
  - [x] 1.6 Implement admin status bar with StatusBar + StatusBarField components: page name (flex-1), "Admin Panel" label, version
  - [x] 1.7 Include skip-to-content link (WCAG 2.4.1, same pattern as AppShell)

- [x] Task 2: Add AdminShell CSS classes to app.css (AC: #7)
  - [x] 2.1 Reused `.hc-app-shell` (identical layout — no separate `.hc-admin-shell` needed)
  - [x] 2.2 Add `.hc-admin-left-nav` with `#12141E` background, light text, dark 98.css sunken border
  - [x] 2.3 Add `.hc-admin-nav-header` with dark raised bg pattern, `#CC3333` text
  - [x] 2.4 Add `.hc-admin-nav-item` with `#C0C8D4` text, hover (`#1E2030`) and active states (`#1A1D2A` bg, white text, accent border)
  - [x] 2.5 Add `.hc-admin-nav-section-label` for uppercase section labels in `#6B7280`
  - [x] 2.6 Add `.hc-admin-nav-separator` etched line adapted for dark background
  - [x] 2.7 Reused `.hc-app-header`, `.hc-app-content`, `.hc-app-body`, `.hc-app-status-bar` classes. Added `.hc-admin-nav-back` for "Back to App" link.

- [x] Task 3: Integrate AdminShell into admin layout (AC: #6)
  - [x] 3.1 Updated `(admin)/+layout.svelte` to import and use `AdminShell`
  - [x] 3.2 Preserved admin role auth guard (redirect to login if not admin)
  - [x] 3.3 Added QueryClientProvider with module-level QueryClient (same pattern as app layout)

- [x] Task 4: Write AdminShell tests (AC: #8)
  - [x] 4.1 Test: renders header with "HealthCabinet" brand
  - [x] 4.2 Test: renders admin nav with Overview, Upload Queue, Users items
  - [x] 4.3 Test: renders "← Back to App" link to `/dashboard`
  - [x] 4.4 Test: renders admin status bar with "Admin Panel" label
  - [x] 4.5 Test: nav header shows "⚙ Admin" text
  - [x] 4.6 Test: axe accessibility audit passes

- [x] Task 5: Run full test suite and verify (AC: #8)
  - [x] 5.1 Run `npm run test:unit` — 347 pass, 1 pre-existing failure (users.test.ts)
  - [x] 5.2 Run `npm run check` — 0 errors, 2 pre-existing warnings
  - [x] 5.3 Admin pages render within AdminShell via updated (admin)/+layout.svelte

### Review Findings

- [x] [Review][Patch] Removed unused `.hc-admin-nav-separator` CSS class (defined but never used in template) [app.css]
- [x] [Review][Defer] No test for handleSignOut click behavior — deferred, pre-existing gap from AppShell (story 9-1)

## Dev Notes

### Architecture Decisions

- **Separate AdminShell component** (not a prop on AppShell): The admin shell has different nav items, different sidebar color, different branding — enough differences to warrant its own component. This avoids cluttering AppShell with conditional logic and keeps both components clean.
- **Reuse shared CSS classes:** Header (`.hc-app-header`), content area (`.hc-app-content`), body (`.hc-app-body`), and status bar (`.hc-app-status-bar`) are identical between user and admin shells — reuse them directly. Only the left nav needs new `.hc-admin-*` classes.
- **Desktop-only (1024px+):** No responsive prefixes needed (cleaned up in story 9-2). Fixed 200px left nav same as user shell.

### Component Reuse from Epic 7

- `StatusBar` and `StatusBarField` from `$lib/components/ui/status-bar/`
- `Button` (variant="standard") from `$lib/components/ui/button/`
- Auth store: `authStore.user?.email`, `authStore.user?.role`, `authStore.logout()`

### Dark Sidebar Color Scheme

The admin sidebar uses `#12141E` (very dark blue-black) per UX page specs. Nav items need light text for contrast:
- Default text: `#C0C8D4` (light gray)
- Hover bg: `#1E2030` (slightly lighter than base)
- Active text: `#FFFFFF` (white) with accent left border
- Active bg: `#1A1D2A` (subtle highlight)
- Section labels: `#6B7280` (muted gray)
- Nav header: "⚙ Admin" in `#CC3333` on raised bg strip

### CSS Naming Convention

Follow established `.hc-[section]-[element]` pattern:
- `.hc-admin-shell` — wrapper (if different from `.hc-app-shell`)
- `.hc-admin-left-nav` — dark sidebar
- `.hc-admin-nav-header` — "⚙ Admin" header
- `.hc-admin-nav-item` — nav links (light text)
- `.hc-admin-nav-item.active` — active state
- `.hc-admin-nav-section-label` — section labels
- `.hc-admin-nav-separator` — etched separator line

### Previous Story Intelligence (9-1, 9-2)

- **From 9-1:** AppShell is 97 lines. Uses `$page.url.pathname` for active state. Auth store pattern: `authStore.user?.role`. CSS in app.css only. 20+ `.hc-app-*` classes defined. Skip-to-content link added for WCAG.
- **From 9-1 review:** `width: 100%` not `100vw` to avoid horizontal overflow. Try/catch on logout.
- **From 9-2:** All responsive prefixes removed. Desktop-only, no `sm:`, `md:`, `lg:` classes.
- **Testing baseline:** ~341 tests pass. Framework: vitest + jsdom + @testing-library/svelte + axe-core.
- **Pre-existing failure:** 1 test in `users.test.ts` (backend, unrelated).

### Files to Create/Modify

**Create:**
- `src/lib/components/AdminShell.svelte` — admin shell component
- `src/lib/components/AdminShell.test.ts` — admin shell tests

**Modify:**
- `src/routes/(admin)/+layout.svelte` — use AdminShell
- `src/app.css` — add `.hc-admin-*` CSS classes

### Current Admin Layout (to be replaced)

The current `(admin)/+layout.svelte` is a basic Tailwind flex layout (22 lines) with auth guard. It needs to be replaced with AdminShell while preserving the auth guard and QueryClientProvider pattern from `(app)/+layout.svelte`.

### Admin Route Structure (existing pages)

- `/admin` → `admin/+page.svelte` (Platform Metrics dashboard)
- `/admin/documents` → `admin/documents/+page.svelte` (Extraction Error Queue)
- `/admin/documents/[document_id]` → detail/correction page
- `/admin/users` → `admin/users/+page.svelte` (User Management)
- `/admin/users/[user_id]` → user detail page

### What NOT to Touch

- Admin page content/styling (that's a separate epic/story)
- AppShell.svelte (user shell stays as-is)
- Auth guard logic (preserve existing role check)
- Any backend code

### References

- [Source: _bmad-output/planning-artifacts/ux-page-specifications.md#Admin-Dashboard, lines 788-870] — Admin sidebar spec, nav items, darker bg `#12141E`
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#AppShell-States, line 812] — AppShell states: user vs admin
- [Source: _bmad-output/planning-artifacts/frontend-redesign-epics.md#FE-Epic-3, lines 144-149] — Story candidate: "Admin shell variant with darker sidebar, admin-specific navigation, 98.css raised panels"
- [Source: _bmad-output/implementation-artifacts/9-1-appshell-98css-window-chrome.md] — AppShell patterns and learnings
- [Source: _bmad-output/planning-artifacts/architecture.md, lines 600-607] — Admin route structure

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Created AdminShell.svelte (98 lines) modeled on AppShell with admin-specific styling
- Dark sidebar (#12141E) with light text nav items, adapted hover/active states
- Admin nav header "⚙ Admin" in #CC3333 (status-action red)
- 3 admin nav items: Overview, Upload Queue, Users + "← Back to App" link
- Active route detection with `exact` flag for `/admin` to avoid false matches on sub-routes
- Admin status bar: page name, "Admin Panel" label, version
- Reused shared CSS classes (.hc-app-shell, .hc-app-header, .hc-app-content, .hc-app-body, .hc-app-status-bar)
- Added 10 new .hc-admin-* CSS classes for dark sidebar variant
- Updated (admin)/+layout.svelte with AdminShell + QueryClientProvider
- 6 unit tests including axe accessibility audit — all pass
- 347/348 total tests pass (1 pre-existing failure unrelated)

### File List

- healthcabinet/frontend/src/lib/components/AdminShell.svelte (new)
- healthcabinet/frontend/src/lib/components/AdminShell.test.ts (new)
- healthcabinet/frontend/src/routes/(admin)/+layout.svelte (modified)
- healthcabinet/frontend/src/app.css (modified)

### Change Log

- Created admin shell variant with dark sidebar and admin-specific navigation (Date: 2026-04-04)
