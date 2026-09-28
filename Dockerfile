# The whole site in one container (Render): Nuxt serves the pages on $PORT and forwards /api to the
# FastAPI application (the modular monolith, allegro.main) on 127.0.0.1:8000.
# Uploaded files live in S3-compatible storage (Yandex Object Storage, Cloudflare R2), the data in PostgreSQL (Neon).
#
#   docker build -t allegro . && docker run -p 3000:3000 --env-file backend/.env.production allegro
#
# docker-compose.yml runs the same image locally together with PostgreSQL and MinIO (an S3 stand-in).

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

COPY backend/allegro ./allegro
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
COPY --from=web /web/.output /app/web
COPY start.sh /app/start.sh

# Never run as root
# (a writable uploads folder, used only when files are kept on local disk: STORAGE_BACKEND=local)
RUN useradd --create-home --uid 1000 allegro && chmod +x /app/start.sh \
    && mkdir -p /app/backend/media && chown allegro /app/backend/media
USER allegro

EXPOSE 3000
CMD ["/app/start.sh"]
