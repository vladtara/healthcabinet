# HealthCabinet — Page-by-Page UI Specification

**Author:** Sally (UX Designer)
**Date:** 2026-03-25
**Companion:** Open `ux-page-mockups.html` in your browser for visual reference.

> **Desktop-only MVP (1024px+).** All mobile and tablet specifications in this document are deferred to post-MVP. Design and implement for desktop breakpoints only (1024px–2560px).

---

## Table of Contents

1. [Design System Quick Reference](#1-design-system-quick-reference)
2. [App Layout Shell](#2-app-layout-shell)
3. [Landing Page `/`](#3-landing-page)
4. [Login `/login`](#4-login-page)
5. [Register `/register`](#5-register-page)
6. [Onboarding `/onboarding`](#6-onboarding)
7. [Dashboard `/dashboard` ★ NEW](#7-dashboard)
8. [Documents `/documents`](#8-documents-cabinet)
9. [Upload `/documents/upload`](#9-document-upload)
10. [Settings `/settings`](#10-settings--medical-profile)
11. [Admin `/admin` ★ NEW](#11-admin-dashboard)
12. [Shared Component Inventory](#12-shared-component-inventory)
13. [Gap Analysis — Current vs Spec](#13-gap-analysis)

---

## 1. Design System Quick Reference

Tokens already defined in `ux-design-specification.md`. Quick-access for this doc:

### Colors

| Token | Hex | Tailwind Mapping |
|---|---|---|
| `surface-base` | `#0F1117` | `bg-background` (custom) |
| `surface-card` | `#1A1D27` | `bg-card` |
| `surface-elevated` | `#22263A` | `bg-accent` / `bg-muted` |
| `border-subtle` | `#2E3247` | `border-border` |
| `text-primary` | `#F0F2F8` | `text-foreground` |
| `text-secondary` | `#8B92A8` | `text-muted-foreground` |
| `text-muted` | `#4E5568` | `text-muted` (custom) |
| `accent` | `#4F6EF7` | `text-primary` / `bg-primary` |

### Health Status Tokens

| Token | Hex | Label | Usage |
|---|---|---|---|
| `status-optimal` | `#2DD4A0` | Optimal | Value within ideal range |
| `status-borderline` | `#F5C842` | Borderline | Worth monitoring |
| `status-concerning` | `#F08430` | Concerning | Outside normal range |
| `status-action` | `#E05252` | Action needed | Significantly out of range |

### Typography (Inter)

| Level | Size | Weight | CSS Class |
|---|---|---|---|
| display | 32px | 700 | `text-[32px] font-bold` |
| h1 | 24px | 600 | `text-2xl font-semibold` |
| h2 | 20px | 600 | `text-xl font-semibold` |
| h3 | 16px | 600 | `text-base font-semibold` |
| body | 15px | 400 | `text-[15px]` |
| label | 13px | 500 | `text-[13px] font-medium` |
| micro | 11px | 400 | `text-[11px]` |

### Spacing Base: 4px

Scale: 4, 8, 12, 16, 20, 24, 32, 48, 64px

---

## 2. App Layout Shell

**Applies to:** All authenticated pages (`/dashboard`, `/documents`, `/settings`, etc.)

### Desktop (≥1024px)

```
┌─────────────────────────────────────────────────────────────┐
│  ⚕ HealthCabinet                              (logo)       │
│─────────────────────────────────────────────────────────────│
│ ▮ SIDEBAR (240px)   │        MAIN CONTENT                  │
│                      │        (flex-1, max-w: 1280px)       │
│ ● Dashboard          │                                      │
│   Documents          │   Page header                        │
│   Trends             │   ─────────────────────              │
│   Profile            │                                      │
│                      │   Page content...                    │
│                      │                                      │
│                      │                                      │
│ ─────────────────    │                                      │
│ user@email.com       │                                      │
└─────────────────────────────────────────────────────────────┘
```

### Tablet (768–1023px)

- Sidebar collapses to icon-only (56px) with labels on hover
- Content area fills remaining width

### Mobile (<768px)

```
┌────────────────────────┐
│   Page content         │
│   (full-width, 16px    │
│    horizontal padding) │
│                        │
│                        │
│                        │
├────────────────────────┤
│ 📊  📁  📈  👤       │
│ Dash Docs Trend Prof  │
└────────────────────────┘
        ↑ Bottom tab bar
```

### Sidebar Implementation

```svelte
<!-- Sidebar nav item -->
<a href="/dashboard"
   class="flex items-center gap-3 px-5 py-2.5 text-[13px] font-medium
          text-muted-foreground border-l-[3px] border-transparent
          hover:text-foreground hover:bg-accent
          {isActive ? 'text-foreground bg-primary/[.08] border-l-primary' : ''}">
  <span class="w-[18px] text-center text-sm">{icon}</span>
  {label}
</a>
```

**Nav items:**

| Icon | Label | Route | Badge (optional) |
|---|---|---|---|
| 📊 | Dashboard | `/dashboard` | — |
| 📁 | Documents | `/documents` | Count of processing docs |
| 📈 | Trends | `/dashboard#trends` | (future) |
| 👤 | Profile | `/settings` | — |

---

## 3. Landing Page

**Route:** `/`
**Layout:** Public (no sidebar, no auth guard)
**Status:** ✅ Built — needs visual upgrade

### Wireframe

```
┌──────────────────────────────────────────────┐
│  ⚕ HealthCabinet        [Sign In] [Get Started]
│──────────────────────────────────────────────│
│                                              │
│                                              │
│         Your health data,                    │
│         finally understood.                  │
│                                              │
│    Upload lab results. Get AI-powered        │
│    interpretation in plain language.          │
│    Track trends across time.                 │
│                                              │
│        [ Create Free Account → ]             │
│                                              │
│    🔒 AES-256    🇪🇺 EU data    🛡️ GDPR     │
│                                              │
└──────────────────────────────────────────────┘
```

### Component Breakdown

| Element | Component | Props/Details |
|---|---|---|
| Top nav | Custom `<nav>` | Logo left; Sign In (ghost button), Get Started (primary button) right |
| Hero heading | `<h1>` | `text-[40px] font-bold`, "finally understood" in `text-primary` (accent) |
| Subtitle | `<p>` | `text-base text-muted-foreground`, max-w-[600px], centered |
| CTA | `<Button>` | Primary, large: `py-3.5 px-8 text-base rounded-[10px]` |
| Trust signals | Inline flex | 3 items: icon + text, `text-[11px] text-muted`, gap-6 |

### States

| State | Behavior |
|---|---|
| Authenticated user visits | Redirect to `/dashboard` |
| Unauthenticated | Show landing page |

### Responsive

- Mobile: reduce hero h1 to `text-[28px]`, stack nav vertically, trust signals wrap
- Tablet: same as desktop, smaller padding

---

## 4. Login Page

**Route:** `/login`
**Layout:** Auth (centered, no sidebar)
**Status:** ✅ Built

### Wireframe

```
┌──────────────────────────────────┐
│                                  │
│          Sign In                 │
│   Access your HealthCabinet      │
│   account.                       │
│                                  │
│   Email                          │
│   ┌────────────────────────┐     │
│   │ you@example.com        │     │
│   └────────────────────────┘     │
│                                  │
│   Password                       │
│   ┌────────────────────────┐     │
│   │ ••••••••               │     │
│   └────────────────────────┘     │
│                                  │
│   ⚠ Invalid email or password    │  ← only if error
│                                  │
│   [ Sign In ]                    │
│                                  │
│   Don't have an account?         │
│   Register                       │
│                                  │
└──────────────────────────────────┘
```

### Component Breakdown

| Element | Component | Details |
|---|---|---|
| Container | `<div>` | `max-w-md p-8`, vertically centered in viewport |
| Title | `<h2>` | `text-2xl font-semibold` |
| Subtitle | `<p>` | `text-muted-foreground mt-2` |
| Email input | `<Input>` | `type="email"`, autocomplete="email" |
| Password input | `<Input>` | `type="password"`, autocomplete="current-password" |
| Error | `<p>` | `role="alert"`, `text-sm text-destructive` |
| Submit | `<Button>` | Full-width primary |
| Link | `<a>` | To `/register`, underlined |

### States

| State | UI Change |
|---|---|
| Default | Empty form |
| Submitting | Button text → "Signing in...", disabled |
| 401 error | Red text: "Invalid email or password" |
| Server error | Red text: "Something went wrong, please try again" |
| Success | Redirect to `/dashboard` |

### Accessibility

- `aria-describedby` on inputs when error shown
- `role="alert"` on error message for screen reader announcement
- All inputs have associated `<Label>`

---

## 5. Register Page

**Route:** `/register`
**Layout:** Auth (centered, no sidebar)
**Status:** ✅ Built

### Wireframe

```
┌────────────────────────────────────┐
│ ┌────────────────────────────────┐ │
│ │         (📄 icon)              │ │
│ │     Create your account        │ │
│ │  Securely store, understand,   │ │
│ │  and track your health data.   │ │
│ │                                │ │
│ │  Email address                 │ │
│ │  ┌──────────────────────────┐  │ │
│ │  │ you@example.com          │  │ │
│ │  └──────────────────────────┘  │ │
│ │                                │ │
│ │  Password                      │ │
│ │  ┌──────────────────────────┐  │ │
│ │  │ Minimum 8 characters     │  │ │
│ │  └──────────────────────────┘  │ │
│ │                                │ │
│ │  Confirm password              │ │
│ │  ┌──────────────────────────┐  │ │
│ │  │ Re-enter your password   │  │ │
│ │  └──────────────────────────┘  │ │
│ │  ─────────────────────────     │ │
│ │  ☑ I consent to health data    │ │
│ │    processing. Your data is    │ │
│ │    encrypted in the EU...      │ │
│ │    Privacy Policy              │ │
│ │                                │ │
│ │  [ Create Account ]            │ │
│ │                                │ │
│ │  Already have an account?      │ │
│ │  Sign in                       │ │
│ └────────────────────────────────┘ │
│                                    │
│  🔒 AES-256  🏢 EU data  🛡️ GDPR  │
└────────────────────────────────────┘
```

### Component Breakdown

| Element | Component | Details |
|---|---|---|
| Card wrapper | `<div>` | `max-w-lg`, card surface with border + shadow |
| Icon circle | `<div>` | `w-12 h-12 rounded-full bg-primary/10`, centered |
| Consent section | Checkbox + text | Divider above, checkbox required, privacy link |
| Trust signals | Below card | Not inside card — separate row |

### Validation Rules

| Field | Validation | Trigger |
|---|---|---|
| Email | RFC 5322 basic regex | `onblur` |
| Password | 8 chars min, 72 bytes max | `onblur` (skip if pristine) |
| Confirm password | Must match password | `onsubmit` |
| Consent | Required checked | Disables submit button |

### Error States

| Error | Display Location |
|---|---|
| Email format invalid | Below email input, red text |
| Email already exists (409) | Below email input: "An account with this email already exists" |
| Password too short | Below password input |
| Passwords don't match | Form-level alert |
| Server error | Form-level alert |

### Post-Success Flow

Register → auto-login (set access token) → redirect to `/onboarding`

---

## 6. Onboarding

**Route:** `/onboarding`
**Layout:** Minimal (no sidebar — dedicated flow)
**Status:** ✅ Built
**Steps:** 3 (Basic Info → Health Conditions → Family History)

### Step Indicator Component

```
    ①───────②───────③
     done    current  pending

  Step {currentStep} of {TOTAL_STEPS}
```

| Step State | Visual |
|---|---|
| Done | Filled circle with ✓, accent color |
| Current | Outlined circle with number, accent border + bg tint |
| Pending | Muted circle with number, border-border |
| Connector (done) | 2px solid accent line |
| Connector (pending) | 2px solid border-subtle line |

### Step 1: Basic Information

```
┌─────────────────────────────────────────┐
│  Age              Sex                    │
│  ┌──────┐   [Male] [Female] [Other]     │
│  │ 32   │   [Prefer not to say]         │
│  └──────┘                               │
│                                          │
│  Height (cm)       Weight (kg)           │
│  ┌──────┐          ┌──────┐             │
│  │ 170  │          │ 70   │             │
│  └──────┘          └──────┘             │
│  ─────────────────────────────           │
│                        [ Continue → ]    │
└─────────────────────────────────────────┘
```

**Fields:**

| Field | Type | Validation | Placeholder |
|---|---|---|---|
| Age | number | 1–120, on blur | "e.g. 32" |
| Sex | radio chips | None (optional) | — |
| Height | number | 50–300 cm, on blur | "e.g. 170" |
| Weight | number | 10–500 kg, on blur | "e.g. 70" |

**Sex input:** Styled as radio chip buttons (not a dropdown). Selected state: `border-primary bg-primary/5 font-medium text-primary`. Uses `<input type="radio" class="sr-only">` for accessibility.

### Step 2: Health Conditions

```
┌──────────────────────────────────────────┐
│  Known Conditions                         │
│  ┌─────────────┐ ┌──────────┐ ┌────────┐│
│  │Type 2 Diab. │ │Hypertens.│ │Hypothyr││
│  └─────────────┘ └──────────┘ └────────┘│
│  ┌───────────┐ ┌───────────┐ ┌─────────┐│
│  │HASHIMOTO'S│ │Hyperthyr. │ │Hi Choles││
│  └───────────┘ └───────────┘ └─────────┘│
│  ... (12 preset conditions)              │
│                                          │
│  ┌──────────────────────┐ [Add]          │
│  │ Add another condition │                │
│  └──────────────────────┘                │
│                                          │
│  Current Medications                     │
│  ┌──────────────────────────────────┐    │
│  │ e.g. Levothyroxine 50mcg, ...   │    │
│  └──────────────────────────────────┘    │
│  Separate with commas.                   │
│  ─────────────────────────────           │
│  [ ← Back ]              [ Continue → ]  │
└──────────────────────────────────────────┘
```

**Condition chips:** 12 preset conditions as `<button>` elements with `aria-pressed`. Selected: `border-primary bg-primary text-primary-foreground shadow-sm`. Unselected: `border-border bg-background hover:border-primary/40`.

**Custom conditions:** Added via text input + "Add" button (or Enter key). Appear as removable chips with ✕ icon.

### Step 3: Family History

```
┌──────────────────────────────────────────┐
│  Family Health History                    │
│  ┌──────────────────────────────────┐    │
│  │ Mother: hypertension             │    │
│  │ Father: cardiovascular disease   │    │
│  │                                  │    │
│  │                                  │    │
│  └──────────────────────────────────┘    │
│  Helps AI identify patterns.  78/2,000   │
│  ─────────────────────────────           │
│  [ ← Back ]           [ Complete Setup ] │
└──────────────────────────────────────────┘
```

**Textarea:** `maxlength=2000`, `rows=5`, character counter bottom-right.

### Navigation Logic

| From | Action | Target |
|---|---|---|
| Step 1 | Continue | Save step → Step 2 |
| Step 2 | Continue | Save step → Step 3 |
| Step 2 | Back | Save step → Step 1 |
| Step 3 | Complete Setup | Save profile + step → `/dashboard` |
| Any step | Reload | Resume from saved `onboarding_step` |
| Already completed | Load page | Redirect to `/dashboard` |

---

## 7. Dashboard ★ NEW

**Route:** `/dashboard`
**Layout:** App shell (sidebar + content)
**Status:** ⚠️ Stub — needs full implementation
**Epic:** 3 (FR14–FR17)

### Empty State (no uploads)

```
┌──────────────────────────────────────────────────────┐
│ SIDEBAR │  Your Health Dashboard                      │
│         │  Welcome, Sofia.                            │
│ ● Dash  │                                             │
│   Docs  │  ┌─ AI BASELINE ──────────────────────────┐│
│   Trend │  │ 🧠 Based on your profile (32F,         ││
│   Prof  │  │ Hashimoto's), key biomarkers to track: ││
│         │  │ TSH, Free T4, Ferritin, Hemoglobin...  ││
│         │  │ Upload your first lab result.           ││
│         │  │                                         ││
│         │  │ ⚠ Not a medical diagnosis.             ││
│         │  └─────────────────────────────────────────┘│
│         │                                             │
│         │  ┌── EMPTY STATE (blurred chart behind) ──┐│
│         │  │     📋                                  ││
│         │  │  Upload your first lab result           ││
│         │  │  Your trends and insights appear here.  ││
│         │  │                                         ││
│         │  │  [ 📤 Upload Health Document ]          ││
│         │  │  PDF or photo · Max 20MB                ││
│         │  └─────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Active State (2+ uploads)

```
┌──────────────────────────────────────────────────────┐
│ SIDEBAR │  Health Dashboard          [ 📤 Upload ]    │
│         │  Last upload: Mar 15 · 3 docs              │
│ ● Dash  │                                             │
│   Docs  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐  │
│   Trend │  │  18  │ │   3  │ │   1  │ │     3    │  │
│   Prof  │  │Optim.│ │Bord. │ │Conc. │ │   Docs   │  │
│         │  └──────┘ └──────┘ └──────┘ └──────────┘  │
│         │                                             │
│         │  ┌─ 📈 PATTERN ALERT ─────────────────────┐│
│         │  │ TSH increased 3.2 → 4.1 → 5.8 mIU/L   ││
│         │  │ across last 3 results. Consistent with  ││
│         │  │ undertreated Hashimoto's.               ││
│         │  └─────────────────────────────────────────┘│
│         │                                             │
│         │  ┌─ BIOMARKER TABLE ───────────────────────┐│
│         │  │ Biomarker  Value   Status   Ref   Trend ││
│         │  │ ─────────────────────────────────────── ││
│         │  │ TSH        5.8     ◉ Conc.  0.4-4 ╱╲╱  ││
│         │  │ Free T4    0.8     ◉ Bord.  0.8-1 ╲╲╲  ││
│         │  │ Hemoglobin 13.2    ◉ Opt.   12-16 ───  ││
│         │  │ Ferritin   18      ◉ Bord.  20-200╲╲╲  ││
│         │  │ Vit B12    485     ◉ Opt.   200-9 ───  ││
│         │  └─────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Component Breakdown

| Section | Component | Details |
|---|---|---|
| Page header | Custom | Title + subtitle + Upload button (top-right) |
| AI Baseline (empty) | `AIInterpretationBlock` | Generated from user profile, shows recommended biomarkers |
| Empty state | Custom | Blurred chart preview behind (`filter: blur(6px)`) + upload CTA |
| Stat cards | Card grid | 4 cards: Optimal (green), Borderline (yellow), Concerning (orange), Docs (white) |
| Pattern alert | `AIInterpretationBlock` | Orange left border for concerning trends, cross-upload analysis |
| Biomarker table | Custom `<table>` | Columns: Name, Value (large+colored), Status badge, Reference range, Sparkline SVG |
| Sparklines | Inline `<svg>` | 60×20px, polyline with 3-4 points, colored by latest status |

### Biomarker Table Row Spec

```svelte
<tr class="hover:bg-accent/5 cursor-pointer">
  <td class="font-medium text-[13px]">{biomarker.name}</td>
  <td>
    <span class="text-[18px] font-bold" style="color: {statusColor}">{value}</span>
    <span class="text-[12px] text-muted-foreground ml-1">{unit}</span>
  </td>
  <td><HealthStatusBadge status={biomarker.status} /></td>
  <td class="text-[11px] text-muted">{refRange}</td>
  <td><!-- SVG sparkline --></td>
</tr>
```

**Row click:** Expands inline to show plain-language note + reference range detail (or opens detail view).

### Data Sources

| Data | API Endpoint | Fetch Strategy |
|---|---|---|
| User profile | `GET /api/v1/users/me/profile` | TanStack Query, key: `['profile']` |
| Latest health values | `GET /api/v1/health-data/values` | TanStack Query, key: `['health_values']` |
| Documents count | `GET /api/v1/documents` | TanStack Query, key: `['documents']` |
| AI baseline/insights | `GET /api/v1/ai/dashboard-summary` | TanStack Query, key: `['ai_summary']` |

### Responsive Behavior

| Breakpoint | Change |
|---|---|
| ≥1024px | Full sidebar, 4-column stat grid, full table with sparklines |
| 768–1023px | Icon-only sidebar, 2-column stat grid, simplified table (no sparklines) |
| <768px | Bottom tab bar, single-column stacked stat cards, value cards instead of table |

---

## 8. Documents Cabinet

**Route:** `/documents`
**Layout:** App shell
**Status:** ✅ Built

### Wireframe

```
┌──────────────────────────────────────────────────────┐
│ SIDEBAR │  Documents                    [ Upload ]    │
│         │                                             │
│   Dash  │  ┌───────────┐ ┌───────────┐ ┌──────────┐ │
│ ● Docs  │  │ 📄        │ │ 🖼️        │ │ 📄       │ │
│   Trend │  │ CBC_Panel  │ │ thyroid   │ │ blood    │ │
│   Prof  │  │ Mar 15     │ │ Sep 8     │ │ Jun 20   │ │
│         │  │            │ │           │ │          │ │
│         │  │ ● Complete │ │ ◉ Partial │ │ ● Done   │ │
│         │  │ 1.2MB      │ │ 3.4MB     │ │ 0.8MB    │ │
│         │  └───────────┘ └───────────┘ └──────────┘ │
│         │                                             │
│         │  Detail panel slides from right on click ──▶│
│         │                                             │
└──────────────────────────────────────────────────────┘
```

### States

| State | Behavior |
|---|---|
| Loading | Centered "Loading documents…" text |
| Error | Red alert: "Failed to load documents" |
| Empty | Dashed border box: "No documents yet" + upload CTA |
| With data | Card grid (3 cols lg / 2 cols sm / 1 col xs) |
| Card clicked | Detail panel opens from right (400px width) |

### Document Card Component

```
┌─────────────────────┐
│ 📄  CBC_Panel_Mar... │
│     Mar 15, 2026     │
│                      │
│ ● Completed   1.2 MB│
└─────────────────────┘
```

| Prop | Type | Notes |
|---|---|---|
| `filename` | string | Truncated with `truncate` class |
| `file_type` | string | PDF → 📄, image/* → 🖼️, other → 📎 |
| `created_at` | string | Formatted: "Mar 15, 2026" |
| `status` | enum | completed/processing/pending/partial/failed |
| `file_size_bytes` | number | Formatted: "1.2 MB" |

### Detail Panel

Slide-in from right, 400px width, full-height. Contains:

1. **Header:** "Document Details" + close ✕ button
2. **Doc info:** Icon + filename + date + size
3. **Status badge**
4. **Recovery card** (if partial/failed): `PartialExtractionCard` component
5. **Extracted values:** List of `HealthValueRow` components
6. **Delete button:** Requires confirmation step

### Real-Time Updates (SSE)

- Documents with status `pending` or `processing` get SSE connections
- Terminal events (`completed`/`partial`/`failed`) close connection and invalidate queries
- Max 3 connection errors before giving up on a document
- All connections cleaned up on component destroy

---

## 9. Document Upload

**Route:** `/documents/upload`
**Layout:** Minimal (no sidebar — focused flow)
**Status:** ✅ Built

### State Machine

```
idle → uploading → success → processing → done
                                        → partial
                                        → failed
```

### State: Idle

```
┌──────────────────────────────────────┐
│    Upload Health Document             │
│    PDF or photo for AI analysis       │
│                                       │
│    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│    ╎         📤                   ╎   │
│    ╎  Drop your file here or     ╎   │
│    ╎  click to browse            ╎   │
│    ╎                             ╎   │
│    ╎  [ 📷 Take Photo ]         ╎   │
│    ╎                             ╎   │
│    ╎  PDF, JPEG, PNG · Max 20MB  ╎   │
│    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
└──────────────────────────────────────┘
```

- `DocumentUploadZone` component handles drag-and-drop + file picker
- Mobile: camera capture as primary CTA, file picker as secondary
- Drag-over state: accent border + subtle background tint
- File validation: PDF or image types only, max 20MB

### State: Processing

```
┌──────────────────────────────────────┐
│  Processing your document...          │
│                                       │
│  ✓ Upload complete                    │
│  │                                    │
│  ✓ Reading document                   │
│  │                                    │
│  ● Extracting values...  (active)     │
│  ╎                                    │
│  ○ Generating insights   (pending)    │
└──────────────────────────────────────┘
```

- `ProcessingPipeline` component with SSE-driven stage updates
- 5 stages: Upload → Read → Extract → Generate → Complete
- Active stage: pulsing dot animation
- Failed/partial: terminal event triggers state transition

### State: Partial Extraction

```
┌──────────────────────────────────────┐
│  ⚠ Partial Extraction                │
│                                       │
│  We could read some values but not    │
│  all. Usually caused by blurry photos │
│  or poor lighting.                    │
│                                       │
│  📸 Tips for better results:          │
│  • Good, even lighting — no shadows   │
│  • Flat, dark surface                 │
│  • All text within the frame          │
│                                       │
│  [ Re-upload ]  [ Keep partial ]      │
└──────────────────────────────────────┘
```

- `PartialExtractionCard` component
- Two actions: Re-upload (primary) / Keep partial (secondary)
- 3-tip photo guide always shown
- Failed state is similar but without "Keep partial" option

---

## 10. Settings / Medical Profile

**Route:** `/settings`
**Layout:** App shell (sidebar + content)
**Status:** ✅ Built

### Wireframe

```
┌──────────────────────────────────────────────────────┐
│ SIDEBAR │  Medical Profile                            │
│         │  ✓ Profile updated (auto-hide 3s)          │
│   Dash  │                                             │
│   Docs  │  ┌─ BASIC INFO ───────────────────────────┐│
│   Trend │  │ Age: [32]   Sex: ○M ●F ○O ○Prefer not ││
│ ● Prof  │  │ Height: [165] cm   Weight: [58] kg     ││
│         │  └─────────────────────────────────────────┘│
│         │                                             │
│         │  ┌─ HEALTH CONDITIONS ─────────────────────┐│
│         │  │ [Hashimoto's✓] [Anemia✓] [Type 2 Diab.]││
│         │  │ [Hypertension] [High Cholesterol] ...   ││
│         │  │                                         ││
│         │  │ Medications: [Levothyroxine 50mcg]      ││
│         │  └─────────────────────────────────────────┘│
│         │                                             │
│         │  ┌─ FAMILY HISTORY ────────────────────────┐│
│         │  │ Mother: hypertension, Type 2 Diabetes   ││
│         │  │ Father: cardiovascular disease           ││
│         │  │                                78/2000  ││
│         │  └─────────────────────────────────────────┘│
│         │                                             │
│         │  [ Save Profile ]                           │
└──────────────────────────────────────────────────────┘
```

### Key Differences from Onboarding

| Aspect | Onboarding | Settings |
|---|---|---|
| Layout | No sidebar, wizard steps | Sidebar, single scrollable page |
| Sex input | Styled radio chips | Standard radio buttons |
| Sections | One per step | All visible in cards |
| Submit | "Complete Setup" | "Save Profile" |
| Feedback | Redirect to dashboard | Success toast (auto-hide 3s) |
| Load | From profile or defaults | Always from existing profile |

### States

| State | UI |
|---|---|
| Loading | Fields populated from API |
| Validation error | Red text below field (same rules as onboarding) |
| Save pending | Button text → "Saving...", disabled |
| Save success | Green toast: "Profile updated" (3s auto-hide) |
| Save error | Red alert: "Failed to save profile" |

---

## 11. Admin Dashboard ★ NEW

**Route:** `/admin`
**Layout:** Admin shell (admin sidebar variant)
**Status:** ⚠️ Stub — needs full implementation
**Epic:** 7 (FR34–FR38)

### Admin Sidebar

Different from user sidebar:
- Background: `#12141E` (darker)
- Logo: "⚙ Admin" in `status-action` color (red)
- Nav items: Overview, Upload Queue, Errors, Users, Corrections

### Overview Page Wireframe

```
┌──────────────────────────────────────────────────────┐
│ ADMIN    │  Admin Overview                            │
│ SIDEBAR  │  Platform health at a glance               │
│          │                                             │
│ ● Over.  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │
│   Queue  │  │  47  │ │ 156  │ │   3  │ │   92%    │ │
│   Errors │  │Users │ │ Docs │ │Failed│ │Suc. Rate │ │
│   Users  │  └──────┘ └──────┘ └──────┘ └──────────┘ │
│   Corr.  │                                            │
│          │  ┌─ UPLOAD QUEUE ─────────────────────────┐│
│          │  │ User    File          Status  Stage    ││
│          │  │ ────────────────────────────────────── ││
│          │  │ sofia@  lipid.pdf     ● Proc  Extract  ││
│          │  │ maks@   photo.jpg     ◉ Part  8/14     ││
│          │  │ user3@  cbc_blur.jpg  ✕ Fail  Read     ││
│          │  └────────────────────────────────────────┘│
│          │                                            │
│          │  ┌─ RECENT ERRORS ────────────────────────┐│
│          │  │ Time  Type        Detail          User ││
│          │  │ 17:02 Extraction  OCR conf. 23%  usr3 ││
│          │  │ 16:45 Parsing     Unknown format  maks ││
│          │  └────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Component Breakdown

| Section | Details |
|---|---|
| Stat cards | 4 cards: Total Users, Docs Processed, Failed Today, Success Rate |
| Upload Queue | Table: user (truncated email), file, status badge, pipeline stage, time ago, actions |
| Queue Actions | View (always), Correct (partial docs), Retry (failed docs) |
| Recent Errors | Table: timestamp, error type badge, description, affected user |

### Queue Status Badges

| Status | Badge Class | Color |
|---|---|---|
| Processing | `badge-processing` | Accent blue, pulsing dot |
| Partial | `badge-borderline` | Yellow |
| Failed | `badge-action` | Red |
| Completed | `badge-optimal` | Green |

### Admin Auth Guard

```typescript
// (admin)/+layout.ts
export const ssr = false;

export async function load() {
  const user = authStore.user;
  if (!user || user.role !== 'admin') {
    throw redirect(307, '/login');
  }
}
```

### Data Sources

| Data | API Endpoint |
|---|---|
| Platform stats | `GET /api/v1/admin/stats` |
| Upload queue | `GET /api/v1/admin/queue` |
| Recent errors | `GET /api/v1/admin/errors` |
| User list | `GET /api/v1/admin/users` |

---

## 12. Shared Component Inventory

### Already Built ✅

| Component | Location | Used In |
|---|---|---|
| Button | `lib/components/ui/button/` | All pages |
| Input | `lib/components/ui/input/` | Auth, onboarding, settings |
| Label | `lib/components/ui/label/` | Auth, onboarding, settings |
| Checkbox | `lib/components/ui/checkbox/` | Register |
| Textarea | `lib/components/ui/textarea/` | Onboarding step 3, settings |
| DocumentUploadZone | `lib/components/health/` | Upload page |
| ProcessingPipeline | `lib/components/health/` | Upload page |
| HealthValueRow | `lib/components/health/` | Documents detail panel |
| PartialExtractionCard | `lib/components/health/` | Upload page, documents page |

### Needs Building 🔧

| Component | Priority | Used In |
|---|---|---|
| **AppShell** (sidebar + content) | P0 | Dashboard, Documents, Settings, Admin |
| **HealthStatusBadge** | P0 | Dashboard table, document detail |
| **BiomarkerValueCard** | P1 | Dashboard (mobile), detail views |
| **AIInterpretationBlock** | P1 | Dashboard (baseline + pattern alerts) |
| **TrendChart / Sparkline** | P2 | Dashboard table, trend views |
| **StatCard** | P1 | Dashboard, Admin |
| **AdminTable** | P2 | Admin queue, admin errors |

### AppShell Component Spec

```svelte
<!-- AppShell.svelte -->
<script lang="ts">
  import { page } from '$app/stores';
  interface Props { children: import('svelte').Snippet; }
  let { children }: Props = $props();

  const navItems = [
    { href: '/dashboard', icon: '📊', label: 'Dashboard' },
    { href: '/documents', icon: '📁', label: 'Documents' },
    { href: '/settings', icon: '👤', label: 'Profile' },
  ];
</script>

<div class="flex h-screen">
  <!-- Desktop sidebar -->
  <aside class="hidden lg:flex w-[240px] flex-col border-r border-border bg-card">
    <div class="px-5 py-5 text-base font-bold text-primary">⚕ HealthCabinet</div>
    <nav class="flex-1">
      {#each navItems as item}
        <a href={item.href}
           class="flex items-center gap-3 px-5 py-2.5 text-[13px] font-medium border-l-[3px]
                  {$page.url.pathname === item.href
                    ? 'text-foreground bg-primary/[.08] border-l-primary'
                    : 'text-muted-foreground border-transparent hover:text-foreground hover:bg-accent'}">
          <span class="w-[18px] text-center">{item.icon}</span>
          {item.label}
        </a>
      {/each}
    </nav>
  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-y-auto p-8">
    {@render children()}
  </main>

  <!-- Mobile bottom nav -->
  <nav class="lg:hidden fixed bottom-0 inset-x-0 flex justify-around border-t border-border bg-card py-2">
    {#each navItems as item}
      <a href={item.href} class="flex flex-col items-center text-[10px]
        {$page.url.pathname === item.href ? 'text-primary' : 'text-muted-foreground'}">
        <span class="text-lg">{item.icon}</span>
        {item.label}
      </a>
    {/each}
  </nav>
</div>
```

---

## 13. Gap Analysis — Current vs Spec

### Visual Theme Gap

The existing pages use **light theme** (white backgrounds, slate colors) while the UX spec defines a **dark-neutral theme** (surface-base: #0F1117). This is the largest visual gap.

**Recommendation:** Apply the Windows 98 clinical workstation theme globally via 98.css + Tailwind CSS v4 custom tokens. The mockup HTML file uses the target aesthetic.

### Page-Level Gaps

| Page | Gap | Priority |
|---|---|---|
| **Landing** | Too minimal — no hero copy, no nav, no trust signals | P2 |
| **Login** | Missing card surface (just floating form) | P3 |
| **Register** | ✅ Well-built — closest to spec | — |
| **Onboarding** | ✅ Well-built — matches spec closely | — |
| **Dashboard** | 🔴 Stub — needs full implementation | **P0** |
| **Documents** | Missing sidebar shell — uses standalone layout | P1 |
| **Upload** | ✅ Well-built | — |
| **Settings** | Missing sidebar shell — uses standalone layout | P1 |
| **Admin** | 🔴 Stub — needs full implementation | **P0** |

### Missing Shared Components

| Component | Blocking Pages | Priority |
|---|---|---|
| AppShell (sidebar) | Dashboard, Documents, Settings | **P0** |
| HealthStatusBadge | Dashboard | P0 |
| AIInterpretationBlock | Dashboard | P1 |
| Sparkline SVG | Dashboard | P2 |

### Implementation Order (Recommended)

1. **AppShell** component (sidebar + bottom nav + content slot)
2. **Dashboard — empty state** (AI baseline + upload CTA)
3. **HealthStatusBadge** component
4. **Dashboard — active state** (stat cards + biomarker table)
5. **Admin — overview** (stat cards + queue table + error table)
6. **Landing page upgrade** (hero content + nav)

---

*This document is the developer reference. Open `ux-page-mockups.html` in a browser for the visual companion.*
