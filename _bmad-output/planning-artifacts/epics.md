---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
workflowStatus: complete
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/ux-page-specifications.md'
  - '_bmad-output/planning-artifacts/frontend-redesign-epics.md'
  - '_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-19.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
  - '_bmad-output/planning-artifacts/product-brief-set-bmad-2026-03-06.md'
---

# HealthCabinet - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for HealthCabinet, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**User Account Management**

FR1: A visitor can register with email and password
FR2: A registered user can log in and maintain an authenticated session
FR3: A user can view, edit, and update their medical profile (age, sex, height, weight, conditions, medications, family history)
FR4: A user can permanently delete their account and all associated health data
FR5: A user can export all their health data in a portable format
FR6: A user can view the full history of consent agreements accepted

**Health Document Management**

FR7: A user can upload a health document (photo or PDF) via drag-and-drop or file picker
FR8: The system extracts structured health values from any uploaded document regardless of lab format, language, or country
FR9: The system assigns a confidence score to each extracted value and surfaces low-confidence results to the user
FR10: A user can re-upload a document when extraction quality is insufficient
FR11: A user can view all previously uploaded documents in their health cabinet
FR12: A user can delete any individual document and its extracted data
FR13: The system processes multiple uploaded documents and normalizes values to a unified timeline

**Health Dashboard**

FR14: A user can view current health values with context indicators (optimal / borderline / concerning) relative to demographic reference ranges
FR15: A user with 2+ uploads can view trend lines per biomarker across time
FR16: A user can view personalized test recommendations based on medical profile before any upload
FR17: The system generates a baseline health view from onboarding profile data alone

**AI Health Interpretation**

FR18: A user can receive a plain-language interpretation of every value in an uploaded lab result
FR19: The AI interpretation system scopes all output as informational and not diagnostic
FR20: Each AI interpretation includes a visible reasoning trail showing which data informed each insight
FR21: A user can ask follow-up questions about their health data *(scope change: available to all users, not paid-only)*
FR22: The AI detects patterns across multiple uploads and surfaces cross-panel observations to all users *(scope change: available to all users, not paid-only)*

**Document Processing Feedback**

FR23: A user receives real-time status updates during processing (uploading → reading → extracting → generating insights)
FR24: A user receives a clear, actionable message when processing fails partially or fully
FR25: A user can flag a specific extracted value as potentially incorrect

**Subscription & Billing** *(Phase 2 — deferred from MVP)*

FR26: A visitor can sign up for a free account with access to document cabinet and health dashboard *(Phase 2)*
FR27: A free user can upgrade to a paid subscription to unlock AI health interpretation *(Phase 2)*
FR28: A paid subscriber can cancel their subscription at any time *(Phase 2)*
FR29: A user can view their subscription status and billing history *(Phase 2)*

**Compliance & Data Rights**

FR30: A user must provide explicit consent to health data processing before any data is collected
FR31: The system logs each consent action with timestamp and privacy policy version
FR32: A user can request a full export of all data held about them
FR33: A user can permanently delete all data: documents, extracted values, and AI interaction history

**Admin & Operations**

FR34: An admin can view platform usage metrics (signups, uploads, conversion rate, upload success rate)
FR35: An admin can view a queue of documents that failed extraction or have low confidence scores
FR36: An admin can manually correct an extracted value and log the correction with a reason
FR37: An admin can view and manage user accounts
FR38: An admin can respond to flagged value reports submitted by users

### NonFunctional Requirements

**Performance**

NFR1: App initial load < 3 seconds on standard broadband
NFR2: Dashboard render after authentication < 2 seconds
NFR3: Upload progress indicator visible within 1 second of upload initiation
NFR4: Document processing (extraction + AI interpretation) < 60 seconds for standard lab documents
NFR5: UI remains responsive during background processing — no blocking states

**Security**

NFR6: Health data encrypted at rest (AES-256-GCM); in transit over TLS 1.2+
NFR7: Health data stored in EU-region infrastructure from day one
NFR8: Authentication sessions expire after configurable inactivity period (30 min)
NFR9: Admin access requires separate elevated credentials (role claim in JWT)
NFR10: Health data never transmitted to third-party services without signed Data Processing Agreements
NFR11: All admin value corrections logged: admin ID, timestamp, original value, new value, reason

**Reliability**

NFR12: Upload failures are retryable without re-selecting the file — no data loss on failure
NFR13: Extracted value writes are atomic — all values saved or none (no partial saves, SQLAlchemy transactions)
NFR14: Values below confidence threshold (< 0.7) are surfaced, never silently accepted
NFR15: Platform targets 99% uptime

**Scalability**

NFR16: Architecture supports 10x user growth from MVP baseline without redesign
NFR17: Document processing pipeline handles concurrent uploads without queue starvation
NFR18: Per-user document storage grows indefinitely without performance degradation

**Compliance**

NFR19: No health data collected before consent flow completes on sign-up
NFR20: Consent events logged with: user ID, timestamp, consent type, privacy policy version
NFR21: Data export is both machine-readable and human-readable
NFR22: Account deletion removes all user data within 30 days (GDPR Article 17)
NFR23: Data processing records maintained for regulatory inspection

**Accessibility**

NFR24: Semantic HTML throughout; keyboard navigation for all core flows
NFR25: Color not used as sole indicator — value context uses color + text label
NFR26: Color contrast ratio meets WCAG 2.1 AA minimum (4.5:1)

### Additional Requirements

**Architecture: Starter Template (impacts Epic 1, Story 1)**

- Monorepo structure: `frontend/` (SvelteKit) + `backend/` (FastAPI) + `k8s/` — this is the first implementation story
- Frontend: SvelteKit 2.53.4 + TypeScript strict + Tailwind CSS v4 + 98.css + DM Sans (Google Fonts) + @unovis/svelte 1.6.2 + @tanstack/svelte-query 6.1.0
- Backend: FastAPI 0.135.1 + Python 3.12 + SQLAlchemy 2.0 async + Alembic + ARQ + Redis + Anthropic Claude SDK + structlog + Sentry
- Auth: Custom JWT (MVP) — 15-min access tokens in JS memory; 30-day refresh tokens in httpOnly+Secure+SameSite=Strict cookies; bcrypt password hashing

**Architecture: Infrastructure & Deployment (Vendor-Agnostic Kubernetes)**

- Cloud: Any k8s cluster (EU region) — vendor-agnostic; local: k3d; prod: Hetzner/OVH/Scaleway/any
- Database: CloudNative-PG operator on k8s (PostgreSQL 16 + pgvector extension)
- Object storage: MinIO on k8s (S3-compatible API; presigned URLs; EU-local)
- Container registry: GHCR (GitHub Container Registry)
- CI/CD: GitHub Actions (build → push GHCR → FluxCD image update)
- GitOps: FluxCD + SOPS (age key for secrets; replaces KMS — no cloud provider dependency)
- Monitoring: Prometheus + Grafana (kube-prometheus-stack)
- Error tracking: Sentry
- Ingress: ingress-nginx; SSE timeout >= 120s
- Three environments: dev / staging / prod (Kustomize overlays)

**Architecture: Data & Processing**

- EAV health data schema (`health_values` table: id, document_id, user_id, name, value, unit, reference_low, reference_high, confidence, is_flagged, extracted_at)
- Application-level AES-256-GCM encryption at repository layer only (not service or router layer); age key via SOPS-encrypted in git
- Rate limiting: MVP upload quota enforced via Redis counters (`Depends(rate_limit_upload)`)
- MinIO presigned URLs for direct file uploads; 20MB max enforced at nginx ingress + FastAPI
- ARQ + Redis async job queue: single MVP processing path now; queue prioritization for paid tiers is deferred with billing
- SSE for real-time upload status; events: `document.upload_started → document.reading → document.extracting → document.generating → document.completed | document.failed | document.partial`
- AI pipeline: LangGraph 1.x (implemented StateGraph in `app/processing/graph.py`) + LangChain-Core 1.x adapter seam in `app/ai/`; Anthropic Claude API remains the active provider
- Current graph shape: `load_document → extract_values → persist_values → generate_interpretation? → finalize_document`; vector-enrichment and checkpoint-resume work remain deferred
- LangSmith observability for all LangGraph node traces
- Billing and subscription integration are deferred to Phase 2 and are not part of active MVP implementation

**UX: Responsive Design**

- Desktop-first intent, mobile-first CSS (Tailwind responsive prefixes only — no raw media queries)
- Desktop-only MVP (1024px+ to 2560px). Mobile and tablet deferred to post-MVP.
- Desktop: menu bar + toolbar + sunken content area + status bar. Left nav 180px. Max content width 1280px.
- Windows 98 clinical workstation aesthetic (98.css chrome, beveled panels, sunken data regions)

**UX: Accessibility**

- WCAG 2.1 AA from MVP launch
- `aria-live` regions on ProcessingPipeline stage transitions and AI content generation
- "Skip to main content" link at top of each page
- Focus trap + return-focus on all modals; Escape always dismisses
- `prefers-reduced-motion` respected
- Layout functional at 200% browser zoom
- All icon-only buttons have `aria-label`; all images have `alt` text

**UX: Component Requirements**

- HealthStatusBadge (or HealthValueBadge): color + text label enforced at component level — color never alone (Optimal / Borderline / Concerning / Action needed)
- ProcessingPipeline (or ProcessingStatusBanner): named stage sequential animation with `role="status"` live region
- AIInterpretationBlock (or AiInterpretationCard): disclaimer always present as final natural-language line; no locked monetization state in MVP
- TrendChart (or BiomarkerTrendChart): disabled single-upload state with overlay; accessible data table alternative; `<figure>` + `<figcaption>`
- UploadZone (or DocumentUploadZone): `role="button"`, keyboard accessible (Enter/Space opens picker); drag-over via live region
- Empty states: never voids — always instructional with clear next action

**Readiness Report: Issues Resolved**

- ✅ Issue #1: Email verification — deferred to Phase 2. MVP registration flows directly: register → consent → onboard.
- ✅ Issue #2: Paid AI stories blocked until billing — resolved by removing tier gates entirely. All AI features available to all users.
- ✅ Issue #3: Stripe customer creation in Story 1.2 — resolved by removing Stripe from MVP. Billing deferred to Phase 2.
- 🟡 WARNING (Issue #4): UX spec references React ecosystem — implementation uses SvelteKit equivalents: 98.css + custom Svelte 5 components, @unovis/svelte, SvelteKit form actions + Zod
- 🟡 WARNING (Issue #5): Component naming inconsistency — use architecture names as canonical

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | User registration |
| FR2 | Epic 1 | Login + authenticated session |
| FR3 | Epic 1 | Medical profile CRUD |
| FR4 | Epic 6 | Account + data deletion |
| FR5 | Epic 6 | Portable data export |
| FR6 | Epic 6 | Consent history view |
| FR7 | Epic 2 | Document upload (photo + PDF) |
| FR8 | Epic 2 | Universal value extraction |
| FR9 | Epic 2 | Confidence scoring + surfacing |
| FR10 | Epic 2 | Re-upload flow |
| FR11 | Epic 2 | Document cabinet view |
| FR12 | Epic 2 | Individual document deletion |
| FR13 | Epic 2 | Multi-upload timeline normalization |
| FR14 | Epic 3 | Health values with context indicators |
| FR15 | Epic 3 | Trend lines per biomarker |
| FR16 | Epic 3 | Pre-upload test recommendations |
| FR17 | Epic 3 | Profile-based baseline view |
| FR18 | Epic 4 | Plain-language AI interpretation |
| FR19 | Epic 4 | Informational-only AI scoping |
| FR20 | Epic 4 | Reasoning trail |
| FR21 | Epic 4 | Follow-up Q&A (all users) |
| FR22 | Epic 4 | Cross-upload pattern detection (all users) |
| FR23 | Epic 2 | Real-time processing status |
| FR24 | Epic 2 | Failure/partial extraction messaging |
| FR25 | Epic 2 | Value flagging by user |
| FR26 | Phase 2 | Free account sign-up (billing deferred) |
| FR27 | Phase 2 | Upgrade to paid tier (billing deferred) |
| FR28 | Phase 2 | Subscription cancellation (billing deferred) |
| FR29 | Phase 2 | Billing status + history (billing deferred) |
| FR30 | Epic 1 | Explicit GDPR consent before data collection |
| FR31 | Epic 1 | Consent event logging |
| FR32 | Epic 6 | Full data export |
| FR33 | Epic 6 | Complete data deletion |
| FR34 | Epic 5 | Admin platform metrics |
| FR35 | Epic 5 | Extraction error queue |
| FR36 | Epic 5 | Manual value correction with audit log |
| FR37 | Epic 5 | User account management |
| FR38 | Epic 5 | Flagged value response |

> Cross-cutting note: Epics 7–13 are frontend modernization epics that support the UX delivery of FR1-FR3, FR7-FR25, and FR34-FR38 without changing their primary functional ownership in the MVP coverage map above. See `frontend-redesign-epics.md` for the full initiative description.

## Epic List

> **Implementation Sequence:** Epic 1 → 2 → 3 → 4 → 5 → 6, then Epics 7–13 as the frontend redesign track (98.css migration)
> **Scope change:** All AI features (interpretation, Q&A, pattern detection) available to all users — no tier gating. Subscription/billing deferred to Phase 2.
> **Email verification:** Deferred to Phase 2. MVP registration flows directly: register → consent → onboard.

### Epic 1: Project Foundation & User Authentication

Users can register with GDPR consent, log in and maintain an authenticated session, and complete their medical profile. Story 1.1 bootstraps the monorepo (SvelteKit + FastAPI + k8s) that enables all subsequent development.

**FRs covered:** FR1, FR2, FR3, FR30, FR31

### Epic 2: Health Document Upload & Processing

Users can upload any health document (photo or PDF) via drag-and-drop or file picker, have values extracted with confidence scoring via the LangGraph + Claude pipeline, receive real-time SSE status across named pipeline stages, manage their document cabinet, handle partial/failed extractions gracefully with re-upload guidance, and flag suspect values.

**FRs covered:** FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR23, FR24, FR25

### Epic 3: Health Dashboard & Baseline Intelligence

Users can view their health values with contextual status indicators (Optimal / Borderline / Concerning / Action needed), see trend lines per biomarker across multiple uploads, and receive a personalized baseline with test recommendations from their medical profile alone — before any document is uploaded.

**FRs covered:** FR14, FR15, FR16, FR17

### Epic 4: AI Health Interpretation

Users receive plain-language AI interpretation with a visible reasoning trail for every uploaded result. All AI output is enforced as informational via the `safety.py` pipeline (no diagnostic claims). Follow-up Q&A and cross-upload pattern detection are included in MVP for authenticated users without paid gating.

**FRs covered:** FR18, FR19, FR20, FR21, FR22

### Epic 5: Admin Operations

Admin can view platform usage metrics, work the extraction error/low-confidence/flagged queue with manual value correction and immutable audit logging, manage user accounts (with strict privacy: no health data exposed to admin), and respond to user-flagged value reports.

**FRs covered:** FR34, FR35, FR36, FR37, FR38

### Epic 6: Data Rights & GDPR Compliance

Users can export all health data as a portable ZIP (machine-readable + human-readable), permanently delete all data with ordered cascade cleanup (MinIO → DB) within GDPR's 30-day SLA, and view their full consent history in read-only chronological format.

**FRs covered:** FR4, FR5, FR6, FR32, FR33

### Epic 7: Design System Foundation (98.css Migration)

Replace shadcn-svelte and bits-ui with 98.css, establish DM Sans typography via Google Fonts, define the Windows 98 gray palette + health status color tokens in Tailwind CSS v4, and build base layout primitives (window frames, raised/sunken panels, toolbar, status bar). This is the foundation that all subsequent frontend epics depend on.

**FRs covered (cross-cutting):** FR1–FR3, FR7–FR25, FR34–FR38

### Epic 8: Public & Authentication Surface

Redesign landing, login, and register pages with 98.css window-frame chrome. Align trust signals, hero section, and first-impression quality with the Windows 98 clinical workstation aesthetic.

**FRs covered:** FR1, FR2 | **Dependencies:** Epic 7

### Epic 9: Authenticated Shell & Navigation

Rebuild the AppShell with 98.css window chrome: menu bar (File, View, Records, Tools, Help) + icon toolbar + sunken content area + status bar. Left nav 180px. Admin shell variant with darker sidebar. Remove existing mobile bottom tab bar and tablet responsive code. Desktop-only (1024px+).

**FRs covered:** FR1–FR3, FR7–FR25, FR34–FR38 | **Dependencies:** Epic 7

### Epic 10: Dashboard Redesign

Turn `/dashboard` into the flagship experience. BiomarkerTable as the centerpiece — dense sortable table with inline status indicators, reference ranges, SparklineBar, and expandable detail. PatientSummaryBar header. AIClinicalNote and AIChatWindow integration below results.

**FRs covered:** FR14, FR15, FR16, FR17, FR18–FR22 | **Dependencies:** Epics 7, 9

### Epic 11: Documents Cabinet & Upload Workflow

Redesign document management with 98.css file-explorer patterns. DocumentList table, DocumentDetailPanel as side panel, ImportDialog with retro window chrome and drag-and-drop zone. Processing pipeline with 98.css progress bar and 4 named stages.

**FRs covered:** FR7–FR13, FR23–FR25 | **Dependencies:** Epics 7, 9

### Epic 12: Settings & Data Rights Experience

Redesign profile, settings, consent history, data export, and account deletion UX with 98.css fieldsets, sunken panels, and dialog confirmation flows. Turn settings into a clear ownership and compliance surface.

**FRs covered:** FR3, FR4, FR5, FR6, FR32, FR33 | **Dependencies:** Epics 7, 9

### Epic 13: Admin Experience & Frontend Hardening

Elevate admin from functional stub to product-grade operations console with 98.css chrome. Admin overview with stat cards, extraction error queue, user management. Final hardening pass: accessibility audit, desktop QA (1024px–2560px), visual regression, performance validation.

**FRs covered:** FR34, FR35, FR36, FR37, FR38 | **Dependencies:** Epics 7, 9, plus patterns from Epics 10–12

---

*Epic 5 (Subscription & Billing) from the original plan covering FR26–FR29 has been deferred to Phase 2. All AI features are available to all users at MVP.*
*Stories 6-2 and 6-3 are deferred until after the frontend redesign track (Epics 7–13).*

---

## Epic 1: Project Foundation & User Authentication

Users can register with GDPR consent, log in and maintain an authenticated session, and complete their medical profile. Story 1.1 bootstraps the monorepo (SvelteKit + FastAPI + k8s) that enables all subsequent development.

**FRs covered:** FR1, FR2, FR3, FR30, FR31

### Story 1.1: Monorepo Scaffold & Development Environment

As a **developer**,
I want a working monorepo with SvelteKit frontend, FastAPI backend, and k8s manifests bootstrapped with Docker Compose and GitHub Actions CI/CD,
So that all subsequent development has a consistent, runnable, and deployable foundation.

**Acceptance Criteria:**

**Given** the repository is cloned
**When** `docker compose up` is run
**Then** the SvelteKit frontend starts and is accessible at `localhost:5173`
**And** the FastAPI backend starts and is accessible at `localhost:8000`
**And** `GET /health` returns `200 OK` with `{"status": "ok"}`

**Given** the backend initializes
**When** the application starts
**Then** AES-256-GCM encryption round-trip succeeds: `decrypt(encrypt(plaintext)) == plaintext`
**And** the Alembic initial migration has been applied and `users` and `consent_logs` tables exist in the database

**Given** the monorepo structure
**Then** it contains `frontend/` (SvelteKit 2.53.4, TypeScript strict, Tailwind CSS v4, shadcn-svelte 1.1.1, @unovis/svelte 1.6.2, @tanstack/svelte-query 6.1.0), `backend/` (FastAPI 0.135.1, Python 3.12, SQLAlchemy 2.0 async, Alembic, structlog, Sentry), and `k8s/` (dev/staging/prod Kustomize overlays, FluxCD config, SOPS age key setup)

**Given** the backend module structure
**Then** `app/core/` exists with `config.py`, `database.py`, `security.py`, `encryption.py`, `middleware.py`
**And** domain directories exist: `app/auth/`, `app/users/`, `app/documents/`, `app/processing/`, `app/health_data/`, `app/ai/`, `app/admin/`

**Given** a push to the main branch
**When** GitHub Actions CI runs
**Then** it executes lint + test + build for both frontend and backend
**And** builds and pushes a Docker image to GHCR tagged with the git SHA

**Given** the frontend app routes
**Then** SvelteKit is configured with `export const ssr = false` for authenticated app routes (CSR mode)
**And** Tailwind CSS v4 custom tokens include 4 semantic health status colors (to be finalized in UX stories)

---

### Story 1.2: User Registration with GDPR Consent

As a **visitor**,
I want to register with my email and password after providing explicit GDPR consent,
So that I have an account and my consent is formally recorded before any health data is collected.

**Acceptance Criteria:**

**Given** a visitor is on the registration page
**When** they submit a valid email, a password meeting requirements, and the GDPR consent checkbox is checked
**Then** a user account is created and the password stored as a bcrypt hash
**And** a `consent_logs` row is written with: `user_id`, `timestamp` (UTC), `consent_type="health_data_processing"`, `privacy_policy_version`
**And** the user is redirected to the onboarding flow (Story 1.4)

**Given** a visitor has not checked the GDPR consent checkbox
**When** they attempt to submit the registration form
**Then** the submit button remains disabled and no account is created

**Given** a visitor submits registration with an already-registered email
**When** the request is processed
**Then** a `409 Conflict` response is returned
**And** "An account with this email already exists" is displayed

**Given** a visitor submits with a password shorter than 8 characters
**When** the form is validated
**Then** an inline validation message is shown before submission and the form is not submitted

**Given** a visitor submits with an invalid email format
**When** the form is validated
**Then** an inline validation error is shown before submission

**Given** the `consent_logs` table
**Then** entries are immutable — no update or delete endpoint exists for consent records

---

### Story 1.3: User Login & Authenticated Session

As a **registered user**,
I want to log in with my email and password and maintain a secure session across browser usage,
So that I can access my health data without repeatedly re-authenticating.

**Acceptance Criteria:**

**Given** a registered user submits valid credentials
**When** login is submitted
**Then** a 15-minute access token (JWT) is stored in JS memory (never localStorage)
**And** a 30-day refresh token is set as an `httpOnly`, `Secure`, `SameSite=Strict` cookie
**And** the user is redirected to the dashboard

**Given** an authenticated user makes an API request
**When** the access token is present in JS memory
**Then** all requests include `Authorization: Bearer <token>` and are authorized

**Given** a user's 15-minute access token expires
**When** the next API request is made
**Then** the refresh token cookie is used automatically to obtain a new access token without requiring the user to log in again
**And** the new refresh token replaces the old one (rotation)

**Given** a user is inactive for 30 minutes
**When** the inactivity period elapses
**Then** the session expires, the access token is cleared from memory, and the user is redirected to login with their current route preserved for post-login redirect

**Given** a user submits invalid credentials
**When** the login request is processed
**Then** a `401` response is returned and "Invalid email or password" is displayed (no field-level specificity to prevent enumeration)

**Given** an unauthenticated user navigates to any authenticated route
**When** the route is loaded
**Then** they are immediately redirected to the login page

**Given** a user clicks logout
**When** logout is triggered
**Then** the access token is cleared from JS memory, the refresh cookie is cleared via `POST /auth/logout`, and the user is redirected to the landing page

---

### Story 1.4: Medical Profile Setup & Onboarding

As a **registered user**,
I want to complete my medical profile (age, sex, height, weight, conditions, medications, family history) through a guided onboarding flow,
So that the system can generate a personalized baseline and test recommendations immediately after setup.

**Acceptance Criteria:**

**Given** a newly registered user reaches onboarding
**When** the onboarding flow loads
**Then** a multi-step form is shown with a visible progress indicator showing current step and total steps

**Given** a user fills in age, sex, height, weight, known conditions, current medications, and family history
**When** they advance through each step
**Then** partial progress is saved after each step so the user can resume from where they left off if they close the browser

**Given** the conditions field
**When** a user types and selects a condition
**Then** it is added as a removable chip
**And** multiple conditions can be added; each chip can be removed individually

**Given** a user completes all onboarding steps and submits the final step
**When** the profile is saved
**Then** a `user_profiles` table row is created with all provided fields
**And** the user is redirected to the dashboard

**Given** a user skips an optional profile field
**When** they proceed through onboarding
**Then** onboarding completes successfully and the profile is saved with only the provided fields

**Given** a user already has a completed profile and visits Settings → Profile
**When** the page loads
**Then** the profile form is shown pre-populated with their existing data
**And** changes are saved via `PUT /users/me/profile` and a success confirmation is shown

**Given** a user navigates the onboarding form with keyboard only
**Then** all form elements are reachable via Tab, fields are activatable via Enter/Space, and chip removal is accessible via keyboard

---

## Epic 2: Health Document Upload & Processing

Users can upload any health document (photo or PDF), have values extracted with confidence scoring via the LangGraph + Claude pipeline, receive real-time SSE pipeline status across named stages, manage their document cabinet, handle partial/failed extractions gracefully with re-upload guidance, and flag suspect values.

**FRs covered:** FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR23, FR24, FR25

### Story 2.1: Document Upload & MinIO Storage

As a **registered user**,
I want to upload a health document (photo or PDF) via drag-and-drop or file picker,
So that the system has my document and can begin processing it.

**Acceptance Criteria:**

**Given** an authenticated user is on the upload page
**When** they drag-and-drop or use the file picker to select a file
**Then** the accepted formats are `image/*` and `application/pdf`
**And** the upload zone displays a drag-over state with live region announcement when a file is dragged over it
**And** the `UploadZone` component has `role="button"` and is activatable via Enter/Space for keyboard users

**Given** a user selects a valid file
**When** the upload is initiated
**Then** the backend issues a MinIO presigned URL via `POST /documents/upload-url`
**And** the file is uploaded directly to MinIO using the presigned URL
**And** a `documents` table row is created with `status="pending"` and a processing job is enqueued in ARQ

**Given** a free-tier user has already uploaded 5 documents today
**When** they attempt another upload
**Then** a `429 Too Many Requests` response is returned and "Daily upload limit reached — try again tomorrow" is displayed

**Given** a user attempts to upload a file larger than 20MB
**When** the file is selected
**Then** an error is shown before upload begins: "File too large — maximum size is 20MB"

**Given** an upload fails mid-transfer (network error)
**When** the user retries
**Then** the upload can be retried without re-selecting the file (the file reference is preserved in component state)
**And** no duplicate `documents` rows are created on retry

**Given** a mobile user opens the upload page
**When** the upload zone loads
**Then** it is full-screen with camera access as the primary action (for photographing paper lab printouts)
**And** all touch targets are a minimum of 44x44px

---

### Story 2.2: Real-Time Processing Pipeline & Status

As a **registered user**,
I want to see real-time status updates as my document is processed,
So that I know exactly what's happening and am never left wondering if the upload worked.

**Acceptance Criteria:**

**Given** a document has been uploaded and a processing job is enqueued
**When** the frontend connects to `GET /documents/{id}/status` (SSE stream)
**Then** status events are received in sequence: `document.upload_started` → `document.reading` → `document.extracting` → `document.generating` → `document.completed` (or `document.failed` / `document.partial`)

**Given** the SSE stream is active
**When** each event is received
**Then** the `ProcessingPipeline` component updates to show the current named stage
**And** the component has `role="status"` and uses an `aria-live` region so stage transitions are announced to screen readers

**Given** the processing completes successfully
**When** the `document.completed` event is received
**Then** the @tanstack/svelte-query cache is invalidated for the document list and health values
**And** the user is shown a success state with a link to view their results

**Given** processing fails completely
**When** the `document.failed` event is received
**Then** a clear error state is shown with an actionable recovery message (navigates to Story 2.5 re-upload flow)

**Given** the SSE connection drops
**When** the connection is lost
**Then** the frontend automatically attempts to reconnect using SSE's built-in `EventSource` retry mechanism

**Given** the k8s ingress configuration
**Then** the SSE route has a timeout of >= 120 seconds to prevent premature connection termination

---

### Story 2.3: Universal Value Extraction & Confidence Scoring

As a **registered user**,
I want the system to automatically extract structured health values from my uploaded document regardless of format, language, or lab,
So that I have normalized, queryable health data with clear quality indicators.

**Acceptance Criteria:**

**Given** a document has been uploaded and the ARQ worker picks up the job
**When** the LangGraph extraction pipeline runs
**Then** Claude's multi-modal API is called with the document (image or PDF) to extract health values
**And** each extracted value is stored as a `health_values` row with: `document_id`, `user_id`, `name`, `value` (encrypted via AES-256-GCM at repository layer), `unit`, `reference_low`, `reference_high`, `confidence` (0.0–1.0)

**Given** the extraction completes
**When** values are written to the database
**Then** all values for the document are written in a single SQLAlchemy transaction (atomic — all saved or none)
**And** the document `status` is updated to `completed`, `partial`, or `failed` accordingly

**Given** one or more extracted values have `confidence < 0.7`
**When** the document processing completes
**Then** the document is marked `partial` (not silently accepted)
**And** low-confidence values are flagged for user review

**Given** multiple documents exist for the same user
**When** a new document is processed
**Then** biomarker values from all documents are linked to a unified per-user timeline (queryable by `name` across all `document_id` values for the user)

**Given** a document in a non-English language or from an unusual lab format
**When** extraction runs
**Then** the LangGraph pipeline still produces structured output (Claude handles multi-lingual and format variation)
**And** the `user_id` on every `health_values` row matches the authenticated user making the request (no cross-user data leakage)

**Given** the LangGraph pipeline
**Then** LangSmith tracing is enabled per `document_id` so every node execution is observable

---

### Story 2.4: Document Cabinet & Individual Document Management

As a **registered user**,
I want to view all my uploaded documents in one place and manage them individually,
So that I have full visibility and control over my health document library.

**Acceptance Criteria:**

**Given** an authenticated user visits the Documents section
**When** the page loads
**Then** all their documents are displayed as cards sorted by upload date (newest first)
**And** each card shows: document thumbnail or type icon, upload date, processing status badge (`Processing` / `Completed` / `Partial` / `Failed`), and document name

**Given** a document is still being processed
**When** the document cabinet is open
**Then** the processing status badge updates in real-time without a page reload (via @tanstack/svelte-query cache invalidation from SSE events)

**Given** a user clicks on a document card
**When** the document detail view opens
**Then** all extracted health values for that document are shown with their confidence indicators

**Given** a user chooses to delete a document
**When** they confirm the deletion dialog
**Then** the document row, all associated `health_values` rows, and the MinIO object are all deleted
**And** the deletion is atomic — if any step fails, the entire deletion is rolled back
**And** the document disappears from the cabinet immediately

**Given** a user has no uploaded documents
**When** the Documents page loads
**Then** an empty state is shown with a clear call-to-action to upload their first document (never a blank void)

**Given** a user views the cabinet on a mobile device
**Then** the card layout is responsive and all touch targets meet the 44x44px minimum

---

### Story 2.5: Re-Upload Flow & Partial Extraction Recovery

As a **registered user**,
I want clear guidance and a smooth re-upload path when my document produces a partial or failed extraction,
So that I can recover gracefully without losing my progress or feeling frustrated.

**Acceptance Criteria:**

**Given** a document processing completes with `status="partial"` (some values below confidence threshold)
**When** the user views the document result
**Then** a `PartialExtractionCard` is shown displaying the successfully extracted values alongside a "We couldn't read everything clearly" message
**And** a 3-tip photo guide is shown: good lighting, flat surface, no shadows

**Given** a document processing completes with `status="failed"` (extraction produced no usable values)
**When** the user views the result
**Then** a clear failure message is shown with the same 3-tip photo guide and a prominent re-upload CTA

**Given** a user clicks re-upload for a partial or failed document
**When** they select a new file
**Then** the new upload replaces the previous attempt for that document slot (no duplicate records created)
**And** any previously extracted partial values from the original attempt are preserved until the new extraction succeeds

**Given** a user decides the partial extraction is acceptable
**When** they choose "Keep partial results"
**Then** the partial values are retained as-is and the re-upload prompt is dismissed

**Given** a re-upload completes successfully
**When** the new extraction finishes
**Then** the document `status` is updated to `completed` and the full set of values replaces the partial set

---

### Story 2.6: Value Flagging

As a **registered user**,
I want to flag an extracted health value that looks incorrect,
So that I can signal potential extraction errors for admin review without losing my other results.

**Acceptance Criteria:**

**Given** an authenticated user is viewing extracted health values for a document
**When** they hover over (or focus on) a value card
**Then** a flag button appears inline next to the value

**Given** a user clicks the flag button on a value
**When** the flag action is submitted
**Then** the `health_values` row is updated: `is_flagged=true`
**And** a visual indicator shows the value is now flagged
**And** the value remains visible in the dashboard (flagging does not hide the value)

**Given** a flagged value
**When** an admin views the extraction error queue (Story 6.2)
**Then** the flagged value appears in the queue with the value name, document ID, and flag timestamp

**Given** a user flags a value using keyboard navigation
**Then** the flag button is reachable via Tab and activatable via Enter/Space
**And** flagging state change is announced via an `aria-live` region

---

## Epic 3: Health Dashboard & Baseline Intelligence

Users can view their health values with contextual status indicators (Optimal / Borderline / Concerning / Action needed), see trend lines per biomarker across multiple uploads, and receive a personalized baseline with test recommendations from their medical profile alone — before any document is uploaded.

**FRs covered:** FR14, FR15, FR16, FR17

### Story 3.0: Registration & Onboarding UI Refinement

As a **new user**,
I want the registration and onboarding pages to reflect HealthCabinet's intended product design language,
So that the first experience feels trustworthy, polished, and consistent with the rest of the application before Epic 3 dashboard work begins.

**Acceptance Criteria:**

**Given** a visitor opens the registration page
**When** the page renders
**Then** the layout uses the approved HealthCabinet UI direction rather than a raw scaffolded form
**And** the page feels visually aligned with the product's professional, trust-first design language
**And** the form remains fully functional with existing registration behavior unchanged

**Given** a visitor views the registration page on desktop or mobile
**When** the page layout adapts across breakpoints
**Then** spacing, typography, form hierarchy, and call-to-action treatment are responsive and intentional
**And** the page avoids the current "unstyled/internal tool" appearance

**Given** a newly registered user enters onboarding
**When** the onboarding flow loads
**Then** the multi-step experience uses the same refined visual language as registration
**And** step progress, section grouping, and field hierarchy are easier to scan and complete
**And** the experience feels like guided product onboarding, not a placeholder admin form

**Given** a user navigates registration or onboarding with keyboard only or assistive technology
**When** they move through the flow
**Then** all accessibility behavior from Stories 1.2 and 1.4 is preserved
**And** visual refinement does not reduce contrast, focus visibility, or form usability

**Given** the UI refinement is complete
**When** the team reviews Epic 3 start readiness
**Then** registration and onboarding are considered visually acceptable foundations for the dashboard and AI experience to follow
**And** no Stripe, billing, or upgrade UI is introduced as part of this refinement

**Scope note:** This story is a UX refinement pass on already implemented flows. It does not change business logic, API contracts, or MVP monetization scope.

### Story 3.1: Profile-Based Baseline & Test Recommendations

As a **registered user**,
I want to see a personalized health baseline and panel recommendations immediately after completing my profile — before uploading any documents,
So that the product delivers value from my first session and I know exactly what tests are worth tracking for me.

**Acceptance Criteria:**

**Given** a user has completed their medical profile (Story 1.4)
**When** they visit the dashboard with no uploaded documents after the Epic 3 UI refinement baseline is in place
**Then** a baseline view is displayed showing 3–5 personalized test recommendations with suggested testing frequency
**And** the recommendations are tailored to the user's profile (e.g., thyroid panels for a user with Hashimoto's; lipid panel for a healthy 28-year-old male)
**And** the view is generated from profile data only — no `health_values` query is made

**Given** a user with no diagnosed conditions
**When** the baseline loads
**Then** age- and sex-appropriate general health panel recommendations are shown

**Given** a user with one or more diagnosed conditions
**When** the baseline loads
**Then** condition-specific recommendations are shown alongside general recommendations

**Given** the baseline view is displayed
**When** the user has no uploads
**Then** an "Upload your first document" CTA is prominently shown
**And** chart areas display an empty-state overlay (never blank axes or broken charts)

**Given** the dashboard renders after authentication
**When** the page loads
**Then** the baseline content appears within 2 seconds (NFR2)
**And** skeleton loaders are shown during the data fetch (never a blank flash)

---

### Story 3.2: Health Values Dashboard with Context Indicators

As a **registered user**,
I want to view my extracted health values with clear contextual status indicators,
So that I can understand whether each value is normal, borderline, or concerning without needing medical training.

**Acceptance Criteria:**

**Given** a user has at least one successfully processed document
**When** they visit the dashboard
**Then** all extracted health values are displayed as value cards
**And** each card shows: biomarker name, value with unit, and a `HealthValueBadge` with one of four states: `Optimal` / `Borderline` / `Concerning` / `Action needed`

**Given** a `HealthValueBadge` is rendered
**Then** it always shows both a color and a text label — color is never the sole indicator (NFR25)
**And** the color contrast ratio meets WCAG 2.1 AA minimum of 4.5:1 (NFR26)

**Given** a value card is rendered
**Then** a plain-language note is shown alongside the status badge explaining what the value means in context (no orphaned numbers)

**Given** reference ranges are demographic-adjusted
**When** a user's age and sex are available from their profile
**Then** the reference range used for status determination matches their demographic group

**Given** one or more values have `confidence < 0.7`
**When** the dashboard renders
**Then** a `ConfidenceWarning` indicator is shown on those value cards

**Given** a user navigates the dashboard with keyboard
**Then** all value cards are reachable via Tab and focusable with visible focus indicators

**Given** the dashboard renders after authentication
**When** the page loads
**Then** content appears within 2 seconds (NFR2)
**And** skeleton loaders are shown for each value card during the fetch

---

### Story 3.3: Biomarker Trend Visualization

As a **registered user with 2 or more uploads**,
I want to see trend lines per biomarker across time,
So that I can understand whether my health values are improving, worsening, or stable.

**Acceptance Criteria:**

**Given** a user has 2 or more processed documents with overlapping biomarkers
**When** they view a biomarker trend
**Then** a `BiomarkerTrendChart` is displayed showing the value over time with data points for each upload date
**And** a reference band showing the optimal range is overlaid on the chart
**And** hovering over (or focusing on) a data point shows a tooltip with the exact value, unit, and upload date

**Given** a user has only one processed document
**When** they view the trend section for a biomarker
**Then** the chart renders in a disabled state with an "Upload another document to unlock trends" overlay
**And** the disabled state does not show broken or empty axes

**Given** a `BiomarkerTrendChart` is rendered
**Then** it is wrapped in a `<figure>` element with a `<figcaption>` describing the biomarker and date range
**And** an accessible data table alternative is available for screen reader users (same data in tabular format)

**Given** a new document is successfully processed
**When** the `document.completed` SSE event is received
**Then** the @tanstack/svelte-query cache is invalidated and trend charts update automatically without a page reload

**Given** a user views the dashboard on mobile (< 768px)
**Then** inline sparklines are hidden and only the full chart view is shown to preserve readability

---

## Epic 4: AI Health Interpretation

Users receive plain-language AI interpretation with a visible reasoning trail for every uploaded result. All AI output is enforced as informational via the `safety.py` pipeline (no diagnostic claims). All authenticated users get follow-up Q&A and cross-upload pattern detection — no tier gating.

**FRs covered:** FR18, FR19, FR20, FR21, FR22

### Story 4.1: Plain-Language AI Interpretation

As a **registered user**,
I want to receive a plain-language interpretation of every value in my uploaded lab result,
So that I understand what my results mean without needing medical expertise.

**Acceptance Criteria:**

**Given** a document has been successfully processed (Story 2.3)
**When** the LangGraph `generate_interpretation` node runs
**Then** Claude produces a plain-language interpretation covering all extracted values
**And** the interpretation passes through `safety.py`: `inject_disclaimer()` appends a non-diagnostic disclaimer as natural language (not a footnote), `validate_no_diagnostic()` rejects any output containing specific diagnoses or treatment recommendations, and `surface_uncertainty()` explicitly flags values the AI cannot reliably interpret

**Given** the interpretation is generated
**When** it is stored
**Then** the interpretation text is stored encrypted (AES-256-GCM) in the `ai_memories` table with `user_id` and `document_id`
**And** no vector-memory row is required in the current MVP baseline; cross-session embedding enrichment remains deferred

**Given** any authenticated user views a document result
**When** the `AiInterpretationCard` renders
**Then** the full interpretation is displayed with the non-diagnostic disclaimer as the final line of natural language
**And** the `AiInterpretationCard` is visually distinct from regular content (separate container, clear AI attribution)

**Given** the AI interpretation renders
**Then** an `aria-live` region announces when content finishes generating

**Given** the Anthropic Claude API is called
**Then** a signed Data Processing Agreement (EU-compatible DPA) is in place
**And** no user health data is sent to any AI provider without a DPA

---

### Story 4.2: AI Reasoning Trail

As a **registered user**,
I want to see which data informed each AI insight,
So that I can trust the interpretation and understand what it's based on.

**Acceptance Criteria:**

**Given** an AI interpretation has been generated for a document
**When** the user views the `AiInterpretationCard`
**Then** a "Show reasoning" toggle is visible but collapsed by default

**Given** a user expands the reasoning trail
**When** the toggle is activated
**Then** the source data behind each insight is shown: which biomarker values were referenced, which reference ranges were consulted, and (for users with 2+ uploads) which prior documents were compared

**Given** the reasoning trail expands
**When** the content appears
**Then** the expansion is announced via an `aria-live` region

**Given** the AI explicitly could not reliably interpret a value
**When** the reasoning trail is shown
**Then** that uncertainty is surfaced explicitly: "Insufficient data to interpret this value confidently"

**Given** a prior document's interpretation was used as context (cross-session RAG)
**When** the reasoning trail is shown
**Then** the prior document is referenced by date so the user can see which historical data informed the current insight

---

### Story 4.3: Follow-Up Q&A

As a **registered user**,
I want to ask follow-up questions about my health data and receive AI responses grounded in my full history,
So that I can explore my results beyond the initial interpretation.

**Acceptance Criteria:**

**Given** any authenticated user views the Q&A section
**When** they submit a follow-up question
**Then** `POST /ai/chat` is called with the question and the full context from `ai_memories` for that user
**And** the response is streamed back and rendered incrementally

**Given** a Q&A response is generated
**When** it passes through `safety.py`
**Then** the same constraints apply as Story 4.1: non-diagnostic disclaimer, no treatment recommendations, uncertainty surfaced

**Given** a Q&A response is being streamed
**When** content is arriving
**Then** an inline skeleton loader is shown until the first token arrives
**And** the response renders incrementally as tokens stream in

**Given** an unauthenticated request hits `POST /ai/chat`
**When** the request is processed
**Then** `401 Unauthorized` is returned

---

### Story 4.4: Cross-Upload Pattern Detection

As a **registered user with multiple uploads**,
I want the AI to detect patterns across my upload history and surface notable observations,
So that I can catch trends my doctor might miss between appointments.

**Acceptance Criteria:**

**Given** a user has 2 or more processed documents
**When** the AI pattern detection runs at the `generate_interpretation` node
**Then** cross-upload patterns are detected (e.g., a biomarker consistently trending in one direction)
**And** the pattern is surfaced as a distinct `PatternCard` component separate from the per-document interpretation

**Given** a pattern is detected and the `PatternCard` renders
**Then** it includes: a plain-language description of the pattern, the uploads it spans (by date), and a "discuss this with your doctor" recommendation
**And** it never states a diagnosis or recommends specific medications or treatments

**Given** a user has only one processed document
**When** the pattern section renders
**Then** it is not shown (no empty or broken state — the section is simply absent)

**Given** an unauthenticated request hits the pattern detection endpoint
**When** the request is processed
**Then** `401 Unauthorized` is returned

---

## Epic 5: Admin Operations

Admin can view platform usage metrics, work the extraction error/low-confidence/flagged queue with manual value correction and immutable audit logging, manage user accounts (with strict privacy: no health data exposed to admin), and respond to user-flagged value reports.

**FRs covered:** FR34, FR35, FR36, FR37, FR38

### Story 5.1: Admin Platform Metrics Dashboard

As an **admin**,
I want to view key platform usage metrics at a glance,
So that I can monitor the health of the platform and identify issues early.

**Acceptance Criteria:**

**Given** an authenticated admin visits the admin dashboard
**When** the page loads
**Then** the following metrics are displayed: total signups, total uploads, upload success rate (completed / total), documents in error/partial state (count), and AI interpretation completion rate

**Given** the metrics page loads
**When** the data is fetched
**Then** all queries are scoped to the admin's platform view — no individual user health data is exposed
**And** metrics are calculated from the database on page load (non-real-time; manual refresh)

**Given** a request is made to any `/api/v1/admin/` endpoint
**When** the JWT is missing the `role=admin` claim
**Then** `403 Forbidden` is returned

**Given** a regular user attempts to access the admin dashboard URL directly
**When** the route loads
**Then** they are redirected to their user dashboard

---

### Story 5.2: Extraction Error Queue & Manual Value Correction

As an **admin**,
I want to view documents with extraction problems and manually correct wrong values with a logged reason,
So that users get accurate health data even when the AI pipeline makes mistakes.

**Acceptance Criteria:**

**Given** an admin views the extraction queue
**When** the page loads
**Then** all documents with `status="failed"`, `status="partial"`, any value with `confidence < 0.7`, or any value with `is_flagged=true` are listed
**And** each entry shows: document ID, user ID (not name), upload date, status, and flag reason if applicable

**Given** an admin selects a document from the queue
**When** they view its extracted values
**Then** each value is shown with its current value, unit, confidence score, and a correction form

**Given** an admin submits a corrected value
**When** the correction is saved
**Then** an `audit_logs` row is written (immutable, append-only) with: `admin_id` (from JWT, never from request body), `document_id`, `value_name`, `original_value`, `new_value`, `reason`, `corrected_at` (UTC)
**And** the `health_values` row is updated with the corrected value
**And** the corrected value is immediately visible in the user's dashboard

**Given** an admin corrects a value
**Then** no indicator is shown to the user that the value was admin-corrected (correction is transparent to user experience at MVP)

**Given** an admin attempts to submit a correction without a reason
**When** the form is validated
**Then** the submission is blocked and "Correction reason is required" is shown

---

### Story 5.3: User Account Management & Flag Response

As an **admin**,
I want to view and manage user accounts and respond to flagged value reports,
So that I can support users and maintain platform integrity.

**Acceptance Criteria:**

**Given** an admin visits user management
**When** the page loads
**Then** a searchable list of users is shown with: user ID, registration date, upload count, and account status
**And** no health data (documents, extracted values, AI interpretations) is shown in this view — critical privacy boundary

**Given** an admin clicks on a user
**When** the user detail view opens
**Then** only account metadata is shown: registration date, last login, upload count, account status
**And** health data remains inaccessible to admin in this view

**Given** an admin suspends a user account
**When** they confirm the suspension dialog
**Then** the user's JWT refresh is invalidated (subsequent refresh attempts return `401`)
**And** the user cannot log in until the suspension is lifted

**Given** an admin views flagged value reports
**When** the flag queue is shown
**Then** each entry shows: user ID, document ID, value name, flagged value, flag timestamp
**And** the admin can mark a flag as "reviewed" which removes it from the active queue
**And** marking reviewed triggers Story 5.2's correction flow if a value change is needed

---

## Epic 6: Data Rights & GDPR Compliance

Users can export all health data as a portable ZIP (machine-readable + human-readable), permanently delete all data with ordered cascade cleanup and audit-log redaction handling within GDPR's 30-day SLA, and view their full consent history in read-only chronological format.

**Epic 6 planning baseline:** this epic must account for the Epic 5 data model additions `users.account_status`, `users.last_login_at`, `health_values.flag_reviewed_at`, `health_values.flag_reviewed_by_admin_id`, and admin correction records in `audit_logs`. It must also preserve `consent_logs` even though the current schema still uses a user-delete cascade that would remove them.

**FRs covered:** FR4, FR5, FR6, FR32, FR33

### Story 6.1: Full Data Export

As a **registered user**,
I want to download a complete export of all data held about me,
So that I can exercise my GDPR Article 20 right to data portability.

**Acceptance Criteria:**

**Given** an authenticated user requests a data export
**When** `POST /users/me/export` is called
**Then** a ZIP file is streamed back containing:
- `documents/` — all uploaded documents (decrypted from MinIO)
- `health_values.csv` — all extracted values (decrypted) with columns: document_id, biomarker_name, canonical_biomarker_name, value, unit, reference_low, reference_high, confidence, needs_review, is_flagged, flagged_at, flag_reviewed_at, extracted_at
- `ai_interpretations.csv` — all AI interpretation texts (decrypted from `ai_memories`) with document_id and created_at
- `admin_corrections.csv` — all admin correction records linked to the user's documents or health values at export time with columns: document_id, value_name, original_value, new_value, reason, corrected_at
- `consent_log.csv` — full consent history with timestamp and policy version
- `summary.txt` — human-readable account summary including account metadata such as registration date, account_status, and last_login_at when present

**Given** the export is generated
**When** it is streamed
**Then** all encrypted values are decrypted at the repository layer before inclusion
**And** the `user_id` is taken from the authenticated JWT (never from the request body — no IDOR possible)
**And** no page reload is required; the download initiates directly from the browser

**Given** a user has no uploaded documents
**When** they request an export
**Then** a valid ZIP is returned containing only `consent_log.csv` and `summary.txt` (no empty error)

---

### Story 6.2: Account & Data Deletion

As a **registered user**,
I want to permanently delete my account and all associated health data,
So that I can exercise my GDPR Article 17 right to erasure.

**Acceptance Criteria:**

**Given** an authenticated user initiates account deletion
**When** they request deletion
**Then** a confirmation dialog is shown requiring them to type their email address to confirm the irreversible action

**Given** the user confirms deletion
**When** the deletion is processed
**Then** the following DB cascade executes in ONE atomic transaction (in order):
1. `audit_logs` rows where the deleted user is the SUBJECT (`user_id` match) are redacted in place: `user_id`, `document_id`, `health_value_id` → `NULL`; `original_value`, `new_value` → `"[REDACTED]"`; `admin_id`, `value_name`, `reason`, `corrected_at` are **preserved** (admin accountability)
2. `audit_logs` rows where the deleted user is the ACTOR (`admin_id` match) have `admin_id` nulled; content is preserved (those rows concern other users' data)
3. The `users` row is deleted. FK CASCADE handles `health_values`, `ai_memories`, `documents`, `user_profiles`, `subscriptions`. `audit_logs.document_id` / `health_value_id` are further nulled by FK `SET NULL` where not already nulled in step 1.
**And** `consent_logs` rows are **retained** via FK `SET NULL` on `user_id` (regulatory requirement — consent records preserved for audit)
**And** `flag_reviewed_at` / `flag_reviewed_by_admin_id` disappear with the deleted `health_values` rows
**And** after the DB transaction commits, a deferred ARQ job (`reconcile_deleted_user_storage`) is enqueued to delete the user's MinIO prefix `{user_id}/`. MinIO failure is logged for operator intervention but does not block the 204 response (design decision: DB-erasure is authoritative for GDPR Article 17 compliance; object-storage cleanup is best-effort post-commit with idempotent reconciliation). See Story 14-2 rationale.

**Given** the DB transaction
**When** it executes
**Then** it is atomic across all DB steps (audit redaction, cascade delete, user delete): if any DB step fails, the entire transaction rolls back and the user is shown a 500 error with an RFC 7807 problem response
**And** partial DB deletion never occurs

**Given** the deletion completes successfully
**When** the DB cascade finishes
**Then** the user's JWT is immediately invalidated (subsequent requests return `401`; the auth dependency rejects tokens for non-existent users)
**And** the user is redirected to the landing page with a "Your data has been deleted" confirmation
**And** the DB transaction completes synchronously within the request; MinIO cleanup runs asynchronously via the deferred job (satisfying the 30-day SLA with same-day DB erasure)

**Given** a user attempts to re-authenticate after deletion
**When** login is submitted with their old credentials
**Then** `401 Unauthorized` is returned (account no longer exists)

---

### Story 6.3: Consent History View

As a **registered user**,
I want to view the full history of consent agreements I have accepted,
So that I have transparency over what I agreed to and when.

**Acceptance Criteria:**

**Given** an authenticated user visits Settings → Privacy
**When** the consent history page loads
**Then** all `consent_logs` rows for that user are displayed in descending chronological order (most recent first)
**And** each entry shows: consent type, timestamp (UTC, human-readable), and privacy policy version

**Given** the consent history is displayed
**Then** it is read-only — no edit or delete controls are shown
**And** the privacy policy version is shown as a link to `/privacy?version={v}`, which resolves to a live marketing page (Story 6-3 ships an MVP stub with the version heading; full legal-authored content is deferred — see `deferred-work.md`)

**Given** any registered user views their consent history
**Then** at least one entry always exists (the registration consent logged in Story 1.2)

**Given** the query executes
**Then** results are filtered strictly by `user_id` from the JWT — no user can view another user's consent history

---

## Epics 7–13: Frontend Redesign Track (98.css Migration)

The frontend redesign replaces shadcn-svelte with 98.css for a Windows 98 clinical workstation aesthetic, establishes DM Sans typography, and targets desktop-only MVP (1024px+). These epics preserve all existing backend contracts and business behavior while rebuilding the UI layer. Full initiative description in `frontend-redesign-epics.md`.

**Planning baseline:** Frontend-only unless a route is blocked by a missing backend contract. All existing business behavior must be preserved. Stories 6-2 and 6-3 are deferred until after this track completes.

**FRs covered (cross-cutting across Epics 7–13):** FR1, FR2, FR3, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR34, FR35, FR36, FR37, FR38

> Stories for Epics 7–13 are listed as candidates. Full acceptance criteria will be generated via the create-story workflow when each story is ready for development. See `frontend-redesign-epics.md` for story candidates, exit criteria, and dependency details per epic.
