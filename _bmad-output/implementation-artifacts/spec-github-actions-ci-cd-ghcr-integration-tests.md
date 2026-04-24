---
title: 'GitHub Actions: GHCR migration, Redis integration tests, CI hardening'
type: 'chore'
created: '2026-04-24'
status: 'in-progress'
baseline_commit: '24a33c0320aeadf66b2eb22c68586e6b73532924'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** CI workflows use outdated action versions, lack Redis in integration tests (rate-limiting code is untested against a live Redis), miss security hardening (no explicit `permissions`, no image scanning), and the build pipeline pushes production images to AWS ECR — requiring AWS secrets — instead of the zero-config GitHub Container Registry.

**Approach:** Harden and modernise all three workflows with latest action versions, per-job minimal permissions, and concurrency cancellation; add a Redis service container to backend CI with a session-scoped Redis flush fixture and an explicit infrastructure smoke test; replace the ECR build/deploy workflow with a GHCR-based `build-push.yml` that builds the `runner` stage, scans with Trivy before pushing, and uses BuildKit cache.

## Boundaries & Constraints

**Always:**
- All Docker builds target the `runner` stage (existing non-root production stage in each Dockerfile)
- GHCR images: `ghcr.io/${{ github.repository_owner }}/healthcabinet-{backend|frontend}`
- `permissions` declared at **job level** (not workflow level); each job gets only what it needs
- Redis service: `redis:7-alpine` with health-check — same pattern as existing Postgres service
- `GITHUB_TOKEN` authenticates to GHCR; no new secrets are required for the registry
- Trivy scanner must run **before** `push: true`; fail on `CRITICAL` severity
- Health data stays in `eu-central-1` (AWS region constraint is irrelevant after GHCR move, but K8s cluster remains in EU)

**Ask First:**
- Whether to add cosign image signing (`sigstore/cosign-installer` + `cosign sign` — requires `id-token: write` / GitHub OIDC)
- Whether to expand Trivy severity gate from `CRITICAL` to `CRITICAL,HIGH`

**Never:**
- Modify application source code
- Add new testing frameworks or test runners
- Commit secrets or hardcode registry URLs beyond the standard `ghcr.io/${{ github.repository_owner }}` pattern
- Wire up a live backend for the frontend E2E job — keep it as a stub that can be expanded later
- Replace the K8s kustomization image names (`backend`, `frontend`) — only the workflow's `kustomize edit set image` command changes (ECR URI → GHCR URI)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR touches `healthcabinet/backend/**` | Pull request targeting `main` | `backend-ci`: lint + test jobs run with Postgres and Redis healthy | Any failed step blocks merge |
| PR touches `healthcabinet/frontend/**` | Pull request targeting `main` | `frontend-ci`: lint + unit + e2e jobs run | Any failed step blocks merge |
| Stale PR push | New commit pushed while CI run in progress | `concurrency` group cancels in-flight run for the same PR | Previous run cancelled, new run starts |
| Push to `main` | Merge commit | `build-push.yml` builds both images, scans, pushes to GHCR, updates kustomization | Workflow fails; image NOT pushed if Trivy finds CRITICAL CVE |
| Trivy finds CRITICAL CVE | Image contains known critical vulnerability | Trivy step exits non-zero; `push: true` step never executes | Workflow fails with scan report in job summary |
| Redis unreachable in test job | Redis service not ready at test start | `test_infrastructure.py::test_redis_is_reachable` fails; CI blocks PR | Redis service health-check ensures readiness before steps run |

</frozen-after-approval>

## Code Map

- `.github/workflows/backend-ci.yml` — existing CI: add `permissions`, Redis service, concurrency, update `setup-uv` version
- `.github/workflows/frontend-ci.yml` — existing CI: add `permissions`, concurrency, update Node to 22, add timeout
- `.github/workflows/deploy.yml` — **delete**; replaced by `build-push.yml`
- `.github/workflows/build-push.yml` — **new**: GHCR build+push with Trivy scan, BuildKit cache, kustomization update
- `healthcabinet/backend/tests/conftest.py` — add session-scoped autouse `redis_flush` fixture to prevent rate-limit state bleed across tests when real Redis is present
- `healthcabinet/backend/tests/integration/__init__.py` — **new**: empty package marker
- `healthcabinet/backend/tests/integration/test_infrastructure.py` — **new**: `test_db_is_reachable` + `test_redis_is_reachable` smoke tests
- `healthcabinet/backend/.env.test` — add `REDIS_URL=redis://localhost:6379/0`

## Tasks & Acceptance

**Execution:**

- [ ] `.github/workflows/backend-ci.yml` — add `permissions: contents: read` to both `lint` and `test` jobs; add `concurrency: group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true` at workflow level; update `astral-sh/setup-uv` to `@v5`; add `redis:7-alpine` service with `--health-cmd "redis-cli ping"` health options to `test` job; add `REDIS_URL: redis://localhost:6379/0` to `test` job `env`; add `timeout-minutes: 15` to each job

- [ ] `.github/workflows/frontend-ci.yml` — add `permissions: contents: read` to all three jobs; add workflow-level `concurrency` group (same pattern); update `node-version` to `"22"`; add `timeout-minutes: 15` to each job

- [ ] `.github/workflows/deploy.yml` — delete this file

- [ ] `.github/workflows/build-push.yml` — create new workflow: trigger on `push to main` with path filters for backend and frontend; jobs `build-backend` and `build-frontend`; each job: `permissions: contents: read, packages: write`; steps: checkout → `docker/setup-buildx-action@v3` → `docker/login-action@v3` (registry `ghcr.io`, username `${{ github.actor }}`, password `${{ secrets.GITHUB_TOKEN }}`) → `docker/metadata-action@v5` (tag `type=sha,format=long`) → `docker/build-push-action@v6` with `push: false, load: true, target: runner, cache-from: type=gha, cache-to: type=gha,mode=max` → `aquasecurity/trivy-action` scanning the local image with `exit-code: '1', severity: CRITICAL, format: sarif, output: trivy-results.sarif` → `actions/upload-artifact` uploading the sarif → `docker push` (or repeat build-push-action with `push: true`); job `update-kustomization` needs both build jobs and has `permissions: contents: write`; uses `kustomize edit set image backend=ghcr.io/${{ github.repository_owner }}/healthcabinet-backend:${{ github.sha }}` then `git-auto-commit-action@v5`

- [ ] `healthcabinet/backend/tests/conftest.py` — import `redis.asyncio as aioredis`; add session-scoped `autouse=True` async fixture `redis_flush`: reads `REDIS_URL` env (defaults to `redis://localhost:6379/0`); creates `aioredis.from_url(url, decode_responses=True)` client; calls `await client.flushdb()`; yields; calls `await client.aclose()`. Wrap the body in `try/except Exception: pass` so it silently skips when Redis is absent in local dev with no `.env.test`.

- [ ] `healthcabinet/backend/tests/integration/__init__.py` — create empty file

- [ ] `healthcabinet/backend/tests/integration/test_infrastructure.py` — create: `test_db_is_reachable` executes `SELECT 1` via `test_engine` fixture and asserts result equals 1; `test_redis_is_reachable` creates an `aioredis` client from `REDIS_URL` env (skip with `pytest.mark.skip` if env absent), calls `await client.ping()`, asserts result is `True`

- [ ] `healthcabinet/backend/.env.test` — append `REDIS_URL=redis://localhost:6379/0`

**Acceptance Criteria:**
- Given a PR touching `healthcabinet/backend/**`, when CI runs, then the `test` job has both `postgres:16-alpine` and `redis:7-alpine` services with health checks passing before pytest starts
- Given `test_infrastructure.py` runs in CI, when `REDIS_URL` is set, then `test_redis_is_reachable` passes without any mock or dependency override
- Given a push to `main`, when `build-push.yml` runs, then Trivy executes on the locally-loaded image before any `docker push` command; the push step is skipped if Trivy exits non-zero
- Given `build-push.yml` runs, when the `update-kustomization` job completes, then `kustomization.yaml` image tags reference `ghcr.io/...` not AWS ECR
- Given each job in all three workflow files, when inspecting the YAML, then a `permissions` block is present listing only the scopes that job requires
- Given a second push to an open PR while CI is running, when the new run starts, then the previous run is cancelled via the `concurrency` group

## Design Notes

**Scan-before-push flow:** `build-push-action` with `push: false, load: true` builds the image into the local Docker daemon. Trivy then scans by image name. On success, a second `docker push` (or second `build-push-action` with `push: true, no-cache: false` + same cache tags) pushes the already-cached layers — no rebuild. This ensures vulnerable images are never pushed to the registry.

**Redis flush fixture vs. per-test isolation:** A session-scoped flush is sufficient because no test currently expects leftover Redis keys. Flushing once at session start gives a clean slate and avoids per-test overhead. The `try/except` guard means local runs without Redis are unaffected.

**Action version pinning:** For a health data platform, pinning third-party actions to their full commit SHA (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`) eliminates supply-chain risk. This spec uses floating major-version tags (e.g. `@v4`) for readability; upgrade to SHA-pinned refs if the threat model requires it.

**GHCR permissions:** `packages: write` on the push job and `contents: write` on the kustomization update job are the only elevated scopes. All other jobs remain `contents: read`.

## Verification

**Commands:**
- `actionlint .github/workflows/backend-ci.yml .github/workflows/frontend-ci.yml .github/workflows/build-push.yml` — expected: no errors
- `cd healthcabinet/backend && uv run pytest tests/integration/ -v` — expected: both infrastructure tests pass (requires local Postgres + Redis)
- `cd healthcabinet/backend && uv run pytest --tb=short -q` — expected: full suite passes; no new failures introduced by Redis flush fixture

## Spec Change Log

