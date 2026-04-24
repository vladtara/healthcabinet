# prod
# ── deps: install all dependencies (maximises cache reuse on source changes) ──
FROM node:22-alpine@sha256:8ea2348b068a9544dae7317b4f3aafcdc032df1647bb7d768a05a5cad1a7683f AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ── dev: full source + all deps — local development and unit testing ──────────
FROM node:22-alpine@sha256:8ea2348b068a9544dae7317b4f3aafcdc032df1647bb7d768a05a5cad1a7683f AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=development \
    PORT=3000 \
    HOST=0.0.0.0
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]

# ── builder: compile the SvelteKit app ────────────────────────────────────────
FROM node:22-alpine@sha256:8ea2348b068a9544dae7317b4f3aafcdc032df1647bb7d768a05a5cad1a7683f AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── runner: minimal production image ──────────────────────────────────────────
FROM node:22-alpine@sha256:8ea2348b068a9544dae7317b4f3aafcdc032df1647bb7d768a05a5cad1a7683f AS runner
WORKDIR /app

# Least-privilege: run as non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 --ingroup nodejs svelte

# Production dependencies only — keeps image small
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Built app owned by the non-root user
COPY --from=builder --chown=svelte:nodejs /app/build ./build

USER svelte

EXPOSE 3000

# adapter-node reads PORT and HOST from env
ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

CMD ["node", "build"]
