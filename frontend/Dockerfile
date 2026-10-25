# ==============================================================================
# HeatShield Bharat — Frontend Production Container Image
# Multi-stage: Node.js 22 builder -> Alpine Nginx runtime
# ==============================================================================

# Stage 1: Build React/TypeScript bundle
FROM docker.io/library/node:22-alpine AS builder

WORKDIR /app

# Install dependencies using pinned lockfile
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source
COPY . .

# Build argument for API URL (defaults to reverse-proxy route /api/v1)
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Compile TypeScript and produce minified Vite bundle in /app/dist
RUN npm run build

# Stage 2: Minimal Nginx runtime for static hosting and SPA routing
FROM docker.io/library/nginx:alpine AS runtime

# Remove default nginx site
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy production Nginx reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
