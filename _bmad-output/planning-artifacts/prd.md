---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-01b-continue', 'step-12-complete']
classification:
  projectType: 'web_app'
  domain: 'healthcare'
  complexity: 'high'
  projectContext: 'greenfield'
  businessModel: 'B2C SaaS freemium'
  regulatoryContext: 'GDPR (EU/Ukraine MVP), medical software liability framing required'
inputDocuments: ['_bmad-output/brainstorming/brainstorming-session-2026-03-06-1430.md']
workflowType: 'prd'
---

# Product Requirements Document — HealthCabinet

**Author:** DUDE
**Date:** 2026-03-06

---

## Executive Summary

HealthCabinet is a B2C SaaS web application that transforms scattered, uninterpreted medical lab results into a unified personal health intelligence platform. The core problem: people receive lab results — blood panels, cholesterol screens, hormone profiles, imaging summaries — as raw numbers with no context, no history, and no guidance. Labs produce data; nobody produces meaning. HealthCabinet solves this by becoming the single place where all health documents live, organized beautifully, with an AI Personal Doctor that interprets them against the user's full history, profile, and risk factors.

**Target users:** Individual consumers — primarily those managing chronic conditions (diabetes, thyroid disorders, autoimmune disease, cardiovascular risk) who test every 3 months and need trend intelligence, not snapshots. Secondary: health-conscious individuals who self-initiate testing without a doctor's prescription.

**Market:** MVP in Ukraine → EU expansion (GDPR jurisdiction). Web-first, mobile post-MVP. Solo founder. Monetization exists as a future product consideration, but billing is not part of the current MVP implementation scope.

**Project type:** Web Application (React SPA) · **Domain:** Healthcare — High Complexity · **Context:** Greenfield · **Regulatory:** GDPR + Ukrainian data protection law; AI output scoped as informational, not diagnostic; product positioned outside EU MDR Class IIa medical device classification.

### What Makes This Special

The MVP delivers genuine, lasting value — a precision professional dashboard (Bloomberg/Stripe aesthetic, not pastel patient UI) showing visual health trends, organized medical history, and AI-assisted health interpretation without requiring monetization plumbing in the first release.

The differentiation moment: a user uploads their fourth blood panel and the AI says *"Your ferritin has been quietly dropping across your last three results. At this rate you'll be clinically deficient in ~3 months. Here's what typically causes this pattern."* No doctor caught it. No app caught it. The product caught it — because it has memory, context, and a user profile informed from day one.

**Hard constraint:** No gamification, no engagement scores, no streaks. Loyalty earned through genuine medical intelligence only.

---

## Success Criteria

### User Success

- User uploads any lab result document (photo, PDF, any format, any lab) and receives a plain-language interpretation of every value — no jargon, no raw numbers without context
- User with 2+ uploads sees trend visualization for each tracked biomarker across time
- User can articulate their current health state from the dashboard alone, without consulting a doctor for basic interpretation
- User onboarding (profile setup → first upload → first insight) completes in under 5 minutes

### Business Success

- **Primary MVP signal:** Upload-to-interpretation loop works reliably — document parsed correctly, values extracted accurately, AI summary coherent and safe
- **Commercial benchmark:** define pricing and conversion hypotheses after MVP validates the core user loop
- **3-month target:** Real users completing the full loop (upload → dashboard → AI insight → trend tracking)
- **12-month target:** Defined after MVP validation and market signal

### Technical Success

- Universal document parsing extracts structured health values from any lab format, language, or quality (photo or PDF) with >95% accuracy on clean documents
- AI interpretation is factually grounded, scoped as informational, and produces no harmful or medically reckless output
- GDPR-compliant data handling from launch: deletion, export, and consent flows all functional
- No data loss on upload failure

### Measurable Outcomes

- Upload success rate: >95% of submitted documents produce a usable extraction
- Time-to-first-insight: <60 seconds from upload completion to AI summary displayed
- Product validation proxy: repeat usage from users who return to upload and review additional documents
- Retention proxy: users who upload 3+ documents across 3+ separate dates

---

## Product Scope

### Phase 1 — MVP

- Web application (SvelteKit SPA, desktop-only MVP at 1024px+ — mobile deferred to post-MVP)
- Medical onboarding: age, sex, height, weight, family history, known conditions, medications
- Universal document upload: photo + PDF, any lab format, any language
- Automated value extraction, confidence scoring, and normalization
- Dashboard: current values with color-coded context + trend lines across multiple uploads
- Baseline health view generated from profile alone (before any upload)
- Personalized test recommendations based on profile (pre-upload)
- Plain-language AI interpretation per uploaded result
- Real-time upload processing status (uploading → reading → extracting → generating insights)
- Graceful failure handling: partial extraction shown + re-upload prompt with photo guidance
- User flag on extracted values
- Full data deletion + export (GDPR Article 17)
- GDPR consent logging
- Admin dashboard: upload queue, error log, manual value correction, user management, basic metrics

### Phase 2 — Growth (Post-MVP)

- AI Personal Doctor with persistent memory and named persona
- Voice health briefings
- Predictive health trajectories ("at this trend, deficient in ~3 months")
- Dynamic health calendar (smart retest nudges by season and trend)
- Doctor Share Mode (one-click formatted export for physician)
- Multilingual health summary export
- Annual Health Year in Review
- Family health profiles + family plan pricing
- Storage-tier upgrade flow
- SEO-optimized marketing and landing pages

### Phase 3 — Vision

- Native mobile app (PWA → iOS/Android)
- Lab booking marketplace (direct test ordering; labs pay per acquisition)
- Physician verification layer
- EU market expansion with localized compliance

**MVP philosophy:** Experience MVP — the upload → extract → interpret → visualize loop must be complete and polished. No skeleton features. Solo founder; no mid-build scope additions. Billing and Stripe are explicitly deferred until after the core health intelligence loop is proven.

---

## User Journeys

### Journey 1: Sofia — Chronic Condition Manager *(Primary, Success Path)*

**Opening Scene:** Sofia has had Hashimoto's thyroiditis for 4 years. Every 3 months she walks out of a lab with a PDF she barely reads. Her endocrinologist says "TSH is a bit high, let's monitor" — every visit. She has no idea if she's getting better or worse.

**Rising Action:** Sofia completes onboarding in 4 minutes — age, weight, Hashimoto's diagnosis, current levothyroxine dose. The dashboard immediately shows a baseline: *"For a 34-year-old woman with thyroid disease, these are the panels most worth tracking."* She uploads her last lab PDF. Within 45 seconds her values appear — TSH, T3, T4, anti-TPO antibodies — each with a plain-language note: *"Your TSH is slightly above the optimal range for someone on thyroid medication. This doesn't mean you're in danger, but it's worth discussing the dose with your doctor."*

**Climax:** She uploads two previous PDFs. The dashboard draws a trend line. For the first time she sees it — TSH climbing consistently across three consecutive quarters. The AI flags it: *"Your TSH has increased across your last three results. This pattern sometimes indicates the current medication dose is no longer optimal."* She screenshots it and brings it to her appointment. Her doctor adjusts her dose.

**Resolution:** Sofia uploads every panel from now on. She pays for the AI doctor tier. She arrives at every appointment as an informed participant. HealthCabinet became part of her health routine.

**Requirements revealed:** Medical onboarding, multi-upload trend visualization, plain-language interpretation, AI pattern detection across uploads, chronic condition context awareness.

---

### Journey 2: Maks — Proactive Self-Tester *(Primary, Alternative Goal)*

**Opening Scene:** Maks is 28, healthy, gets a private lab panel twice a year. He just received a lipid panel: LDL 4.1, HDL 1.0, triglycerides 2.3 mmol/L. The lab flagged LDL "H". He has no idea if this is bad. Twenty minutes of googling leaves him more confused.

**Rising Action:** He signs up, completes onboarding (no diagnosed conditions). The app recommends 5 panels worth tracking for a healthy male his age. He drags the PDF in. Thirty seconds later his values appear with color-coded context — LDL yellow ("above optimal, not yet clinical concern"), HDL orange ("low — this is the more important number"), triglycerides red ("elevated, often linked to diet and alcohol").

**Climax:** *"Your LDL alone isn't alarming for your age. But low HDL combined with elevated triglycerides is a pattern worth attention — associated with increased cardiovascular risk over time. No action needed today, but worth retesting in 3 months."* Maks finally understands his results. Not scared — informed.

**Resolution:** He retests in 3 months. Triglycerides improve. He continues using the product because the interpretation and tracking loop already feel useful without extra monetization friction.

**Requirements revealed:** Single-upload instant interpretation, color-coded value context, no-condition onboarding path, proactive test recommendations, free tier value without multiple uploads.

---

### Journey 3: Upload Edge Case *(Error Recovery)*

**Opening Scene:** A user photographs a paper lab printout in poor lighting — slightly blurry, tilted, shadow across the middle.

**Rising Action:** They upload. The parser reads some values but confidence is too low on several biomarkers.

**Climax:** *"We could only partially read this document. For accurate results, please upload a clearer image — good lighting, flat surface, no shadows. Here's what we could read so far: [partial values shown]."* A re-upload prompt with a 3-tip photo guide appears.

**Resolution:** Retake succeeds. Full extraction completes. No data lost, no frustration.

**Requirements revealed:** Partial extraction handling, confidence scoring, graceful failure messaging, re-upload flow, visual upload guidance, no silent failures.

---

### Journey 4: Platform Admin — Solo Founder *(Operational)*

**Opening Scene:** Week 3 post-launch. 47 signups, 31 have uploaded at least once.

**Rising Action:** Admin dashboard: upload success rate 91% (target: 95%), 3 documents in failed-extraction queue, 1 support request ("my cholesterol value looks wrong"). Two failed uploads are blurry photos (users notified). One is a new format from a regional Ukrainian clinic.

**Climax:** The AI pulled "6.2" where the correct value was "0.62" — decimal misread. The founder corrects it manually, logs the reason, flags the format for parser improvement, responds to the support request.

**Resolution:** New format added to improvement backlog. Upload rate returns to 94% by end of week.

**Requirements revealed:** Admin dashboard, upload monitoring, extraction error queue, manual value correction with audit log, user management, basic analytics.

---

### Journey Requirements Summary

| Capability | Journeys |
|---|---|
| Medical onboarding (profile + conditions) | Sofia, Maks |
| Universal document upload (photo + PDF) | All |
| Automated value extraction + normalization | All |
| Plain-language AI interpretation | Sofia, Maks |
| Multi-upload trend visualization | Sofia |
| Partial extraction + graceful failure | Edge case |
| Re-upload guidance flow | Edge case |
| AI pattern detection across uploads | Sofia |
| Color-coded value context | Maks |
| Free tier value without AI doctor | Maks |
| Admin: upload monitoring + error queue | Admin |
| Admin: manual correction + user management | Admin |

---

## Domain-Specific Requirements

### Compliance & Regulatory

- **GDPR (primary):** User health data is special category data under GDPR Article 9 — requires explicit, granular consent before collection. Users must be able to access, export, and permanently delete all data. Data processing agreements required for all third-party services (AI providers, cloud storage).
- **Medical software classification:** All AI output framed as *"informational only — not a substitute for professional medical advice."* Keeps product outside EU MDR Class IIa medical device classification — critical for solo founder to avoid CE marking requirements.
- **Ukraine MVP:** Design for GDPR compliance from day one (Law of Ukraine on Personal Data Protection is a subset). GDPR compliance is the superset.
- **No HIPAA:** US-specific; not applicable.

### Technical Constraints

- Health documents and extracted values encrypted at rest (AES-256 or equivalent); all data in transit over TLS 1.2+
- Health data stored in EU-region infrastructure from MVP
- Consent events logged with timestamp and privacy policy version
- All manual admin value corrections logged with admin ID, timestamp, original value, new value, reason
- Health data never shared with advertisers, data brokers, or third parties without explicit user consent

### AI Safety Constraints

- Every AI interpretation includes a non-diagnostic disclaimer as natural part of response language, not a legal footnote
- AI must not produce confident-sounding output for values it cannot reliably interpret — uncertainty surfaced to user
- AI may explain what values suggest and recommend discussing with a doctor; must never recommend specific medications, dosage changes, or treatments
- AI responses tested against scenarios where users might act harmfully on advice before launch

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| AI extracts wrong value (decimal error, unit mismatch) | Confidence scoring per value; admin correction queue; user flag button |
| User acts on AI output as medical advice | Informational framing in every AI response; "discuss with your doctor" always present |
| GDPR violation | Encryption, consent logging, EU data residency, deletion flows at launch |
| Medical device reclassification | Strict "informational only" scope; no diagnostic claims in marketing or UI |
| User trust gap (new platform, sensitive data) | Transparent data practices in UI; "you own your data" messaging; no dark patterns |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Universal Health Document Intelligence**
No existing consumer health product parses arbitrary lab documents from any lab, country, language, or format (photo or PDF) and normalizes them into a unified health timeline. Existing solutions require specific lab integrations or are country-limited. If delivered, this is a genuine replication moat — years of training data and edge case handling.

**2. Context-First Personalization (Cold-Start Solved)**
Most health apps are empty and useless until months of use. HealthCabinet generates a personalized baseline dashboard and test recommendations from onboarding data alone, before the first upload exists. Treating profile data as a first-class input, not metadata, is a novel UX pattern in health products.

**3. AI Health Companion with Persistent Cross-Session Memory**
Existing AI health tools reset context per session. HealthCabinet's AI doctor accumulates context across every upload, conversation, and profile update. Over 12 months it surfaces patterns no single doctor appointment could catch. This "compounding intelligence" model is novel in consumer health.

**4. Consumer Price-Point AI Physician**
€9.99/month anchored against a real doctor visit (€50–150+) is a meaningful market disruption for patient-controlled health intelligence.

### Competitive Landscape

- **Heads Up Health / InsideTracker:** Lab integration imports only; no universal parsing; US-focused; no persistent AI memory
- **Apple Health / Google Health:** Aggregation layer; no interpretation; requires device integrations
- **Generic AI chatbots:** No document parsing; no persistent health memory; no structured trend visualization
- **Gap:** No product combining universal document parsing + persistent AI interpretation + trend visualization + consumer pricing exists in the EU/Ukraine market

### Validation Approach

| Innovation | Validation |
|---|---|
| Universal document parsing | >95% upload success on diverse lab formats from Ukrainian, German, and Polish labs |
| Context-first onboarding | Time-to-first-insight measurement; user comprehension survey after first AI summary |
| Persistent AI memory | Qualitative: "does it feel like it knows you?" after 3+ uploads |
| Consumer AI doctor value | Repeat usage, qualitative trust signal, and demand for deeper AI features after the core loop proves useful |

### Innovation Risks

| Risk | Mitigation |
|---|---|
| Parsing fails on edge cases | Graceful degradation; admin correction queue |
| AI memory produces contradictory outputs over time | Structured memory format; human review of flagged cases |
| AI fatigue / user distrust | Trust-first design; transparent reasoning trail; "you own your data" |
| Replication by well-funded competitor | First-mover advantage in UA/EU; parsing training data depth as moat |

---

## Web Application Requirements

### Architecture

- **Framework:** React (preferred; open for discussion at architecture phase)
- **App type:** SPA — client-side routing, persistent session, no full-page reloads
- **Rendering:** CSR for authenticated app; static/SSR for public marketing pages (post-MVP)
- **State management:** Required — user profile, upload state, health data cache, AI conversation history

### Browser Support

| Browser | Support |
|---|---|
| Chrome (last 2 versions) | Full |
| Firefox (last 2 versions) | Full |
| Safari (last 2 versions) | Full |
| Edge (last 2 versions) | Full |
| IE / Legacy | Not supported |

### Responsive Design

- Desktop-only MVP (1024px+ to 2560px wide desktop). Mobile and tablet support deferred to post-MVP.
- Post-MVP: touch-friendly upload targets for mobile users photographing lab results

### Upload UX

- Drag-and-drop + file picker; accepts image/* and application/pdf
- Max file size defined at architecture phase
- Camera access: optional enhancement, not required for MVP

### SEO

- MVP: not required (app behind authentication; landing page informational only)
- Post-MVP: SSR or static generation for marketing pages (B2C organic growth channel)

---

## Functional Requirements

### User Account Management

- **FR1:** A visitor can register with email and password
- **FR2:** A registered user can log in and maintain an authenticated session
- **FR3:** A user can view, edit, and update their medical profile (age, sex, height, weight, conditions, medications, family history)
- **FR4:** A user can permanently delete their account and all associated health data
- **FR5:** A user can export all their health data in a portable format
- **FR6:** A user can view the full history of consent agreements accepted

### Health Document Management

- **FR7:** A user can upload a health document (photo or PDF) via drag-and-drop or file picker
- **FR8:** The system extracts structured health values from any uploaded document regardless of lab format, language, or country
- **FR9:** The system assigns a confidence score to each extracted value and surfaces low-confidence results to the user
- **FR10:** A user can re-upload a document when extraction quality is insufficient
- **FR11:** A user can view all previously uploaded documents in their health cabinet
- **FR12:** A user can delete any individual document and its extracted data
- **FR13:** The system processes multiple uploaded documents and normalizes values to a unified timeline

### Health Dashboard

- **FR14:** A user can view current health values with context indicators (optimal / borderline / concerning) relative to demographic reference ranges
- **FR15:** A user with 2+ uploads can view trend lines per biomarker across time
- **FR16:** A user can view personalized test recommendations based on medical profile before any upload
- **FR17:** The system generates a baseline health view from onboarding profile data alone

### AI Health Interpretation

- **FR18:** A user can receive a plain-language interpretation of every value in an uploaded lab result
- **FR19:** The AI interpretation system scopes all output as informational and not diagnostic
- **FR20:** Each AI interpretation includes a visible reasoning trail showing which data informed each insight
- **FR21:** A user can ask follow-up questions about their health data
- **FR22:** The AI detects patterns across multiple uploads and surfaces cross-panel observations to users

### Document Processing Feedback

- **FR23:** A user receives real-time status updates during processing (uploading → reading → extracting → generating insights)
- **FR24:** A user receives a clear, actionable message when processing fails partially or fully
- **FR25:** A user can flag a specific extracted value as potentially incorrect

### Subscription & Billing

- **FR26:** Deferred to Phase 2 — a visitor can sign up for a free account with access to document cabinet and health dashboard
- **FR27:** Deferred to Phase 2 — a free user can upgrade to a paid subscription to unlock future monetized features
- **FR28:** Deferred to Phase 2 — a paid subscriber can cancel their subscription at any time
- **FR29:** Deferred to Phase 2 — a user can view their subscription status and billing history

### Compliance & Data Rights

- **FR30:** A user must provide explicit consent to health data processing before any data is collected
- **FR31:** The system logs each consent action with timestamp and privacy policy version
- **FR32:** A user can request a full export of all data held about them
- **FR33:** A user can permanently delete all data: documents, extracted values, and AI interaction history

### Admin & Operations

- **FR34:** An admin can view platform usage metrics (signups, uploads, conversion rate, upload success rate)
- **FR35:** An admin can view a queue of documents that failed extraction or have low confidence scores
- **FR36:** An admin can manually correct an extracted value and log the correction with a reason
- **FR37:** An admin can view and manage user accounts
- **FR38:** An admin can respond to flagged value reports submitted by users

---

## Non-Functional Requirements

### Performance

- App initial load: <3 seconds on standard broadband
- Dashboard render after authentication: <2 seconds
- Upload progress indicator visible: within 1 second of upload initiation
- Document processing (extraction + AI interpretation): <60 seconds for standard lab documents
- UI remains responsive during background processing — no blocking states

### Security

- Health data encrypted at rest (AES-256 or equivalent); in transit over TLS 1.2+
- Health data stored in EU-region infrastructure from day one
- Authentication sessions expire after configurable inactivity period
- Admin access requires separate elevated credentials
- Health data never transmitted to third-party services without data processing agreements
- All admin value corrections logged: admin ID, timestamp, original value, new value

### Reliability

- Upload failures are retryable without re-selecting the file — no data loss on failure
- Extracted value writes are atomic — all values saved or none (no partial saves)
- Values below confidence threshold are surfaced, never silently accepted
- Platform targets 99% uptime (solo-founder managed infrastructure)

### Scalability

- Architecture supports 10x user growth from MVP baseline without redesign
- Document processing pipeline handles concurrent uploads without queue starvation
- Per-user document storage grows indefinitely without performance degradation

### Compliance

- No health data collected before consent flow completes on sign-up
- Consent events logged with: user ID, timestamp, consent type, privacy policy version
- Data export is both machine-readable and human-readable
- Account deletion removes all user data within 30 days (GDPR Article 17)
- Data processing records maintained for regulatory inspection

### Accessibility

- Semantic HTML throughout; keyboard navigation for all core flows
- Color not used as sole indicator — value context uses color + text label
- Color contrast ratio on value indicators meets WCAG AA minimum (4.5:1)
- Post-MVP: full WCAG 2.1 AA audit before EU market launch
