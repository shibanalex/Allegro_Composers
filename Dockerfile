# The whole site in one container, for small/free hosting (Render): Nuxt serves the pages on $PORT
# and forwards /api to the FastAPI app (all services in one process, like dev_server) on 127.0.0.1:8000.
# Uploaded files live in S3-compatible storage (Yandex Object Storage, Cloudflare R2), the data in PostgreSQL (Neon).
#
#   docker build -t allegro . && docker run -p 3000:3000 --env-file backend/.env.production allegro
#
# docker-compose.yml is the other way to run it: every service in its own container behind nginx.

# ---------------------------------------------------------------- 1. build the site
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- 2. run
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=3000 NODE_ENV=production
# Node for the built site (official Node binaries only need glibc 2.28+, which the Python image has)
COPY --from=web /usr/local/bin/node /usr/local/bin/node

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/allegro_common ./allegro_common
COPY backend/services ./services
COPY backend/migrations ./migrations
COPY backend/alembic.ini backend/dev_server.py ./
COPY backend/scripts ./scripts
COPY --from=web /web/.output /app/web
COPY start.sh /app/start.sh

# Never run as root
RUN useradd --create-home --uid 1000 allegro && chmod +x /app/start.sh
USER allegro

EXPOSE 3000
CMD ["/app/start.sh"]
