# Multi-stage build: keeps the final image to just the standalone
# server output + static assets, not the full node_modules/build cache.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN useradd --create-home lumen
COPY --from=builder /app/public ./public
COPY --from=builder --chown=lumen:lumen /app/.next/standalone ./
COPY --from=builder --chown=lumen:lumen /app/.next/static ./.next/static
USER lumen

EXPOSE 3000
CMD ["node", "server.js"]
