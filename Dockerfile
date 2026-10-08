# The whole site in one container (Render): the gateway (Caddy) takes $PORT and hands the chat's WebSocket
# to Centrifugo (127.0.0.1:8001) and everything else to Nuxt (127.0.0.1:3001), which forwards /api to the
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

# ---------------------------------------------------------------- 2. the chat's WebSocket server and the gateway
# Official release builds (single static binaries), checked against the checksums their projects publish
FROM python:3.12-slim AS tools
ADD https://github.com/centrifugal/centrifugo/releases/download/v6.9.7/centrifugo_6.9.7_linux_amd64.tar.gz /tmp/centrifugo.tgz
ADD https://github.com/caddyserver/caddy/releases/download/v2.11.7/caddy_2.11.7_linux_amd64.tar.gz /tmp/caddy.tgz
RUN echo "96be0fe54646b59831302b77bfb8a1e71085302998197448ac461bf6880c8b40  /tmp/centrifugo.tgz" | sha256sum -c -     && echo "727b91701a392de6ebc5027509f548bf39979e5216340d0faed8fa5e69c84f8b  /tmp/caddy.tgz" | sha256sum -c -     && tar -xzf /tmp/centrifugo.tgz -C /usr/local/bin centrifugo     && tar -xzf /tmp/caddy.tgz -C /usr/local/bin caddy

# ---------------------------------------------------------------- 3. run
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=3000 NODE_ENV=production
# Node for the built site (official Node binaries only need glibc 2.28+, which the Python image has)
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY --from=tools /usr/local/bin/centrifugo /usr/local/bin/caddy /usr/local/bin/

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/allegro ./allegro
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY backend/scripts ./scripts
COPY --from=web /web/.output /app/web
COPY start.sh /app/start.sh
COPY deploy /app/deploy

# Never run as root
# (a writable uploads folder, used only when files are kept on local disk: STORAGE_BACKEND=local)
RUN useradd --create-home --uid 1000 allegro && chmod +x /app/start.sh \
    && mkdir -p /app/backend/media && chown allegro /app/backend/media
USER allegro

EXPOSE 3000
CMD ["/app/start.sh"]
