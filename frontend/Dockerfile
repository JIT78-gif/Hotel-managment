# Frontend image — Next.js 14, multi-stage build, standalone output
ARG NODE_VERSION=20

# ---- deps ----
FROM node:${NODE_VERSION}-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# Use ci when lockfile exists, fall back to install otherwise
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# ---- builder ----
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Optional: override the WS URL at build time when backend has its own domain (e.g. wss://api.example.com)
ARG NEXT_PUBLIC_BACKEND_WS_URL=""
ENV NEXT_PUBLIC_BACKEND_WS_URL=${NEXT_PUBLIC_BACKEND_WS_URL}
ENV NEXT_TELEMETRY_DISABLED=1

# Ensure public/ exists (Next.js doesn't create one if there are no static assets)
RUN mkdir -p public

RUN npm run build

# ---- runner ----
FROM node:${NODE_VERSION}-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root user for safety
RUN groupadd --system --gid 1001 nodejs \
 && useradd  --system --uid 1001 --gid nodejs nextjs

# Standalone output contains its own minimal node_modules + server.js
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://localhost:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" || exit 1

CMD ["node", "server.js"]
