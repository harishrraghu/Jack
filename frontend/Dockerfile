# ── Stage 1: install deps ─────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
# `npm ci` is faster and strictly reproducible for CI/Docker builds.
RUN npm ci


# ── Stage 2: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

# NEXT_PUBLIC_API_BASE_URL is baked in at build time.
# Override with --build-arg or leave blank to use the runtime default.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN npm run build


# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Run as non-root for security.
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# The standalone output bundles everything needed to run the server.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
# Static assets must be copied separately (not included in standalone).
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
