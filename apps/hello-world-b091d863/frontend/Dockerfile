# syntax=docker/dockerfile:1.7
FROM docker.io/library/node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
# `npm ci` requires a lock file; if absent, `npm install` is used to build it.
RUN if [ -f package-lock.json ]; then npm ci; else npm install --no-audit --no-fund; fi
COPY tsconfig.json vite.config.ts index.html ./
COPY src ./src
RUN npm run build


FROM docker.io/nginxinc/nginx-unprivileged:stable-alpine AS runtime

LABEL org.opencontainers.image.title="hello-world-frontend" \
      org.opencontainers.image.description="Hello World React frontend + nginx reverse proxy" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="apps/hello-world-b091d863"

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx-unprivileged runs as UID 101 (non-root) with the right permissions on /tmp paths.
USER 101:101
EXPOSE 8080
