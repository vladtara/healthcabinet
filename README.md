# HealthCabinet Repository

HealthCabinet is a personal health intelligence platform that turns scattered lab PDFs and photos into structured biomarker history, trend visibility, and plain-language AI interpretation.

This repository contains both the product code and the planning material around it.

## Start Here

- Product setup and developer workflow: [`healthcabinet/README.md`](healthcabinet/README.md)
- Product requirements: [`_bmad-output/planning-artifacts/prd.md`](_bmad-output/planning-artifacts/prd.md)
- Architecture decisions: [`_bmad-output/planning-artifacts/architecture.md`](_bmad-output/planning-artifacts/architecture.md)
- UX system and mockups: [`_bmad-output/planning-artifacts/ux-design-specification.md`](_bmad-output/planning-artifacts/ux-design-specification.md)
- Pitch deck: [`_bmad-output/presentations/healthcabinet-pitch-deck.html`](_bmad-output/presentations/healthcabinet-pitch-deck.html)
- Presentation assets index: [`_bmad-output/presentations/README.md`](_bmad-output/presentations/README.md)

## Repository Map

| Path | Purpose |
| --- | --- |
| `healthcabinet/` | Runtime product code: SvelteKit frontend, FastAPI backend, Docker Compose, and Kubernetes manifests |
| `_bmad-output/` | Generated PRD, architecture, UX, QA, and presentation artifacts |
| `_bmad/` | BMad workflow material and module configuration |
| `.agents/` | Installed local skills and supporting agent workflows |
| `CLAUDE.md` / `AGENTS.md` | Collaboration and repository-specific operating rules |

## Product Snapshot

- Consumers upload health documents in PDF or image form.
- The system extracts biomarker values, preserves document history, and shows results in a clinical table-first UI.
- AI interpretation explains results in plain language and can reason across multiple uploads.
- Admin tooling exists for monitoring, review, and correction workflows.
- Health data is intended to stay in AWS `eu-central-1`.

## Quick Repo Onboarding

```bash
cd healthcabinet
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up -d
```

Then continue with the full setup guide in [`healthcabinet/README.md`](healthcabinet/README.md).

## Documentation Strategy

The repo is split on purpose:

- Use `healthcabinet/` when you are building or running the application.
- Use `_bmad-output/` when you need the product definition, architecture rationale, UX direction, or planning artifacts.
- Use the pitch deck in `_bmad-output/presentations/` when you need a concise narrative for demos, partners, or investors.
