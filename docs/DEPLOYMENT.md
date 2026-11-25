# Deployment

The production image (`Dockerfile`) bundles Caddy, FastAPI, Nuxt SSR, and
Centrifugo in one container launched by `start.sh`.

```
Dockerfile -> start.sh
                |-- alembic upgrade head
                |-- uvicorn allegro.main:app (127.0.0.1:8000)
                |-- node .output/server/index.mjs (127.0.0.1:3001)
                |-- centrifugo (127.0.0.1:8001)
                '-- caddy ($PORT)
```

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Signing secret (48+ chars) for JWTs, reset tokens, and derived keys |
| `DATABASE_URL` | PostgreSQL connection string (`-pooler` / PgBouncer compatible) |
| `STORAGE_BACKEND` | `local` or `s3` |
| `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET` | Object storage coordinates |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Service account credentials for S3 writes |
| `MEDIA_URL_PREFIX` | Public base URL for serving uploaded assets |
| `SETUP_TOKEN` | One-time bootstrap token for `/setup` on an empty database |
| `SITE_URL`, `NUXT_PUBLIC_SITE_URL` | Canonical origin used for CSRF `Origin` checks and SEO links |
| `REDIS_URL` | Optional Redis endpoint for comment caching and distributed rate limits |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Optional SMTP credentials for email notification digests |

Optional limits: `UPLOAD_DAILY_MB` (default `1024`), `MAX_UPLOAD_MB` (default
`200`), `WRITE_REQUESTS_PER_MINUTE`, `SEARCH_REQUESTS_PER_MINUTE`,
`SIGNUPS_PER_HOUR`, `RESET_LINK_TTL_HOURS`.
