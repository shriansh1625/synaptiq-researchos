# SynaptiQ ResearchOS — Next.js frontend
# Build: docker build -f docker/frontend.Dockerfile -t synaptiq-frontend ../frontend

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_DEMO_SESSION_ID=
ARG NEXT_PUBLIC_DEMO_REPORT_ID=
ARG NEXT_PUBLIC_DEMO_QUERY=
ARG NEXT_PUBLIC_DEMO_LABEL=

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_DEMO_SESSION_ID=$NEXT_PUBLIC_DEMO_SESSION_ID
ENV NEXT_PUBLIC_DEMO_REPORT_ID=$NEXT_PUBLIC_DEMO_REPORT_ID
ENV NEXT_PUBLIC_DEMO_QUERY=$NEXT_PUBLIC_DEMO_QUERY
ENV NEXT_PUBLIC_DEMO_LABEL=$NEXT_PUBLIC_DEMO_LABEL

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
