# Repository Guidelines

## Find and read CLAUDE.md

## Project Structure & Module Organization

The product code lives in `healthcabinet/`: `frontend/` for the SvelteKit 2 + Svelte 5 UI, `backend/` for the FastAPI service, and `k8s/` for Kubernetes manifests and overlays. Backend source is under `healthcabinet/backend/app/`; tests are in `healthcabinet/backend/tests/`. Frontend routes and shared code live in `healthcabinet/frontend/src/`, with UI tests colocated as `*.test.ts`. The top-level `_bmad/` directory is workflow material, not application runtime code.

## Build, Test, and Development Commands

From `healthcabinet/`, run `docker compose up -d` to start Postgres, Redis, frontend, and backend, then `docker compose exec backend alembic upgrade head` to apply migrations.

Backend:

- `cd healthcabinet/backend && uv sync` installs Python 3.12 dependencies.
- `uv run uvicorn app.main:app --reload --port 8000` starts the API locally.
- `uv run pytest` runs all backend tests.
- `uv run ruff check . && uv run ruff format . && uv run mypy app/` covers lint, format, and strict typing.

Frontend:

- `cd healthcabinet/frontend && npm install` installs Node 20+ dependencies.
- `npm run dev` starts the Vite dev server.
- `npm run build`, `npm run check`, `npm run lint`, `npm run test:unit`, and `npm run test:e2e` cover build, type checks, linting, unit tests, and Playwright E2E.

## Coding Style & Naming Conventions

Python follows Ruff and strict MyPy settings, with a 100-character line limit and 4-space indentation. Keep modules snake_case and prefer async patterns consistent with SQLAlchemy 2.0. TypeScript/Svelte uses Prettier, ESLint, and Svelte 5 runes; keep component files in PascalCase, utilities in camelCase, and route tests as `page.test.ts` or `*.test.ts`.

## Testing Guidelines

Add backend tests under `healthcabinet/backend/tests/<domain>/test_*.py`. Frontend tests should stay close to the route or component they validate, using Vitest for unit coverage and Playwright for browser flows. Run the smallest relevant test first, then the full suite before opening a PR.

## Commit & Pull Request Guidelines

Recent history mixes short commits (`fix`, `add`) with conventional commits (`feat: ...`). Prefer Conventional Commit format such as `feat: add document upload retries` or `fix: normalize auth email handling`. PRs should include a concise description, linked issue or task, affected areas (`frontend`, `backend`, `k8s`), and screenshots for UI changes. Note any migrations, new environment variables, or rollout concerns explicitly.

## Security & Configuration Tips

Health data is intended to stay in AWS `eu-central-1`. Never commit populated `.env` files or secrets. Use `backend/.env.example`, `frontend/.env.example`, and SOPS-managed Kubernetes secrets as the source of truth.

## Design & UX References

Before implementing any frontend/UI work, consult the UX specifications in `_bmad-output/planning-artifacts/`:

- **`ux-design-specification.md`** — Design system (tokens, colors, typography, component anatomy, accessibility, responsive breakpoints)
- **`ux-page-specifications.md`** — Per-page developer specs with wireframes, component breakdowns, all states, and validation rules
- **`ux-page-mockups.html`** — Open in browser for interactive visual mockups of every page
- **`ux-design-directions.html`** — Interactive design direction showcase

Key conventions: dark-neutral theme (`#0F1117` base), health status badges always use color + text label (never color alone), sidebar layout on desktop / bottom tab bar on mobile, Inter font family.
