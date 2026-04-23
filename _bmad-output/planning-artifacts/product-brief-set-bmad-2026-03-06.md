---
stepsCompleted: [1, 2, 3, 4, 5, 6]
workflowStatus: complete
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-06-1430.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
date: '2026-03-06'
author: DUDE
---

# Product Brief: set-bmad

## Executive Summary

HealthCabinet is a Personal Health Intelligence SaaS for individual consumers who receive lab results as raw numbers — no context, no history, no guidance. The product transforms scattered, uninterpreted medical documents into a unified health intelligence platform: a precision professional dashboard showing visual trends, plus an AI Personal Doctor that interprets results against the user's full history and profile.

MVP targets Ukraine → EU (GDPR). B2C freemium. Web-first. Solo founder.

---

## Core Vision

### Problem Statement

People receive lab results — blood panels, cholesterol screens, hormone profiles — as raw numbers with no interpretation, no trend context, and no memory. Labs produce data; nobody produces meaning. Doctors have 10 minutes. Apps have no memory. The result: patients leave appointments still confused, chronic condition patients can't see if they're improving, and early warning patterns go undetected for months.

### Problem Impact

- Chronic condition patients (thyroid, diabetes, autoimmune, cardiovascular) test every 3 months for life and have no way to see whether they're trending better or worse
- Self-initiating health-conscious individuals get flagged values and spend hours googling, still confused
- Early patterns that compound over months — quietly dropping ferritin, rising TSH — are invisible until they become clinical problems
- Every patient arrives at every appointment at an information disadvantage

### Why Existing Solutions Fall Short

- **Heads Up Health / InsideTracker:** Lab integration imports only; no universal document parsing; US-focused; no persistent AI memory
- **Apple Health / Google Health:** Aggregation layer only; no interpretation; requires device integrations
- **Generic AI chatbots:** No document parsing; no structured health memory; no trend visualization; context resets each session
- **Gap:** No product combining universal document parsing + persistent AI interpretation + trend visualization + consumer pricing exists in the EU/Ukraine market

### Proposed Solution

HealthCabinet gives every person an AI Personal Doctor with full memory of their health story, accessible at €9.99/month — anchored against a real doctor visit (€50–150+), not the app market. The free tier delivers a genuine precision dashboard (Bloomberg/Stripe aesthetic) with trend visualization and organized medical history. The paid tier adds something qualitatively different: an AI that remembers every upload, every conversation, and every profile detail — and surfaces the patterns no single appointment can catch.

The differentiation moment: *"Your ferritin has been quietly dropping across your last three results. At this rate you'll be clinically deficient in ~3 months."* No doctor caught it. No app caught it. HealthCabinet caught it — because it has memory.

### Key Differentiators

1. **Universal document intelligence** — any lab format, any language, any country, photo or PDF — no integrations required
2. **Context-first cold start** — personalized dashboard and test recommendations generated from onboarding profile alone, before the first upload
3. **Compounding AI memory** — AI accumulates context across every upload and conversation; gets more valuable over time, not less
4. **Consumer price-point AI physician** — €9.99/month against a €50–150+ doctor visit is a genuine market disruption
5. **Precision professional positioning** — Bloomberg/Stripe aesthetic targets people who take health seriously, not a pastel patient app

---

## Target Users

### Primary Users

#### Sofia — Chronic Condition Manager *(High-frequency, highest value)*

34-year-old woman with Hashimoto's thyroiditis. Tests every 3 months, has been doing so for 4 years. Walks out of labs with PDFs she barely reads. Her endocrinologist says "let's monitor" every visit. She has no idea if she's improving or getting worse — no trend, no context, no memory across results.

**Motivation:** Understand her own trajectory, arrive at appointments as an informed participant, not a passive patient.
**Workaround:** Googling individual values, asking friends, hoping the doctor catches something.
**Success moment:** Dashboard draws a trend line across three uploads. TSH has been climbing consistently. She screenshots it, brings it to her appointment. Doctor adjusts her dose. For the first time, she drove the conversation.
**Retention driver:** Tests for life — HealthCabinet becomes part of her permanent health routine. Pays for AI doctor tier.

**Segment:** Chronic condition patients (thyroid, diabetes, autoimmune, cardiovascular). Highest frequency, highest retention, highest willingness to pay.

---

#### Maks — Proactive Self-Tester *(Health-conscious, single-upload value)*

28-year-old male, healthy, gets private lab panels twice a year. Receives a lipid panel with a flagged LDL. Spends 20 minutes googling, leaves more confused than when he started.

**Motivation:** Understand what his results actually mean without medical jargon or fear.
**Workaround:** Google, Reddit, sometimes ignores results entirely.
**Success moment:** Color-coded values with plain-language context. "Your LDL alone isn't alarming for your age. But low HDL combined with elevated triglycerides is a pattern worth attention." Not scared — informed.
**Retention driver:** Retests in 3 months. Stays on free tier but considers upgrading to ask the AI about diet impact.

**Segment:** Self-initiating health-conscious individuals. Validate free tier value; potential paid conversion via curiosity and follow-up questions.

---

### Secondary Users

#### Platform Admin — Solo Founder *(Operational)*

The founder operating the platform. Monitors upload success rates, manages the extraction error queue, manually corrects misread values, responds to user-flagged results, tracks conversion metrics.

**Key needs:** Upload monitoring, error queue management, manual value correction with audit log, basic analytics (signups, uploads, conversion rate).
**Success:** Upload success rate ≥95%; error queue cleared weekly; no unresolved user flags older than 48 hours.

---

### User Journey

#### Sofia's Core Journey

**Discovery →** Word of mouth / health community / Google "understand my blood test results"
**Onboarding →** Medical profile in 4 minutes (age, conditions, medications). Dashboard immediately shows baseline: *"For a 34-year-old woman with thyroid disease, these are the panels most worth tracking."*
**First upload →** PDF dropped in. 45 seconds. Values appear with plain-language notes. Not scared — informed.
**Aha moment →** Third upload. Trend line drawn. TSH climbing consistently. AI flags the pattern. She takes it to her doctor.
**Routine →** Every 3-month panel goes into HealthCabinet before the appointment. Paid subscriber. It's now part of her health infrastructure.

#### Maks's Core Journey

**Discovery →** Google after receiving a confusing lab result
**Onboarding →** No diagnosed conditions path. Recommendations for 5 panels worth tracking for his age and sex.
**First upload →** PDF in. 30 seconds. Color-coded values. Plain-language interpretation. Relief.
**Aha moment →** Understanding the relationship between LDL, HDL, and triglycerides — not three separate numbers but a pattern.
**Routine →** Retests in 3 months. Tracks improvement. Considers AI tier to explore diet impact.

---

## Success Metrics

### User Success

- User uploads any lab result (photo, PDF, any format) and receives plain-language interpretation of every value — no jargon, no raw numbers without context
- User with 2+ uploads sees trend visualization per biomarker across time
- User can articulate their current health state from the dashboard alone, without consulting a doctor for basic interpretation
- Onboarding (profile setup → first upload → first insight) completes in under 5 minutes
- Time-to-first-insight: <60 seconds from upload completion to AI summary displayed

### Business Objectives

- **Primary MVP signal:** Upload-to-interpretation loop works reliably — document parsed correctly, values extracted accurately, AI summary coherent and safe
- **3-month target:** Real users completing the full loop (upload → dashboard → AI insight → trend tracking)
- **12-month target:** Defined after MVP validation and market signal

### Key Performance Indicators

| KPI | Target | Timeframe |
|---|---|---|
| Upload success rate | >95% of submitted documents produce usable extraction | From launch |
| Time-to-first-insight | <60 seconds from upload completion | From launch |
| Free→paid conversion | 5–10% of free users upgrade within 60 days of first upload | 60-day cohort |
| Retention proxy | Users who upload 3+ documents across 3+ separate dates | Rolling |
| Onboarding completion | Profile setup → first upload → first insight in <5 minutes | From launch |

**Vanity metrics explicitly excluded:** Total signups without upload activity, page views, session duration without core action completion.

---

## MVP Scope

### Core Features

**MVP philosophy:** Experience MVP — the upload → extract → interpret → visualize loop must be complete and polished. No skeleton features. Solo founder; no mid-build scope additions; managed services for auth, storage, and billing.

**Authentication & Account**
- Email + password registration and authenticated session
- Medical profile (age, sex, height, weight, conditions, medications, family history)
- Full account + data deletion (GDPR Article 17)
- Data export in portable format
- Consent logging (timestamp + privacy policy version)

**Document Upload & Processing**
- Universal upload: photo + PDF, drag-and-drop + file picker
- Automated value extraction, confidence scoring, normalization
- Real-time processing status (uploading → reading → extracting → generating insights)
- Graceful failure: partial extraction shown + re-upload guidance with photo tips
- User flag on any extracted value

**Health Dashboard**
- Color-coded current values with context (optimal / borderline / concerning) vs. demographic reference ranges
- Trend lines per biomarker across 2+ uploads
- Baseline health view generated from profile alone (pre-upload)
- Personalized test recommendations based on profile

**AI Interpretation**
- Plain-language interpretation per uploaded result (free tier)
- Informational framing on every AI output — not diagnostic
- Reasoning trail: expandable "based on" for each insight

**Subscription & Billing**
- Free tier: document cabinet + dashboard
- Paid tier: €9.99/month — AI follow-up questions + cross-upload pattern detection
- Cancel anytime; billing history view

**Admin Dashboard**
- Upload queue, error log, manual value correction with audit log
- User management, basic metrics (signups, uploads, conversion rate, upload success rate)

---

### Out of Scope for MVP

- Named persistent AI companion (persona, voice briefings)
- Predictive health trajectories ("deficient in ~3 months")
- Dynamic health calendar (retest nudges)
- Doctor Share Mode / multilingual export
- Annual Health Year in Review
- Family health profiles
- Storage-tier upgrade flow
- Native mobile app
- Lab booking marketplace
- Physician verification layer
- SEO / SSR marketing pages
- Camera capture (file upload only)

**Hard constraints (never implement):** Gamification, engagement scores, streaks, badges, social health sharing, artificial feature gating on free tier.

---

### MVP Success Criteria

- Upload success rate ≥95% on diverse lab formats (Ukrainian, German, Polish labs)
- Time-to-first-insight <60 seconds
- Free→paid conversion 5–10% within 60 days of first upload
- GDPR flows fully functional at launch (consent, export, deletion)
- No silent extraction failures — every low-confidence result surfaced

**Go/no-go signal for Phase 2:** Real users completing the full loop (upload → dashboard → AI insight → trend tracking) with measurable retention (3+ uploads across 3+ dates).

---

### Future Vision

**Phase 2 — Growth:** Named AI Personal Doctor with persistent memory, voice briefings, predictive trajectories, dynamic health calendar, Doctor Share Mode, multilingual export, Annual Year in Review, family profiles, storage upgrade flow.

**Phase 3 — Platform:** Native mobile app (PWA → iOS/Android), lab booking marketplace (labs pay per acquisition), physician verification layer, EU market expansion with localized compliance.

**3-year vision:** HealthCabinet becomes the personal health operating system for European consumers — the place where all health data lives, interpreted intelligently, with an AI that knows your full history better than any single doctor appointment could.
