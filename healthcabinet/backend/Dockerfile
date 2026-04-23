# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Pin uv to a specific version — avoids silent breakage on upstream changes
COPY --from=ghcr.io/astral-sh/uv:0.11.1 /uv /bin/uv

# UV_LINK_MODE=copy: Docker layers don't support hardlinks — must copy files
# UV_COMPILE_BYTECODE=1: pre-compile .pyc files for faster cold starts
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies only — separate layer so code changes don't bust cache
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# Copy source after deps (cache-friendly ordering)
COPY . .

RUN chmod +x entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["./entrypoint.sh"]

# ── Stage 2: dev/test (includes dev dependencies and uv) ──────────────────────
FROM python:3.12-slim AS dev

COPY --from=ghcr.io/astral-sh/uv:0.11.1 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install all dependencies including dev group (pytest, httpx, mypy, ruff)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY . .

RUN chmod +x entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["./entrypoint.sh"]


# ── Stage 3: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# Non-root user — minimal attack surface
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home --shell /sbin/nologin appuser

# Copy only what the app needs at runtime
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app       /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]
