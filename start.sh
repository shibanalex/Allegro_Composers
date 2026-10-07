#!/bin/sh
# Container entrypoint (see Dockerfile): update the database schema, start the API, then the site.
set -e

cd /app/backend
alembic upgrade head
# Light copies of pictures that don't have one yet (idempotent; in the background, the site doesn't wait)
( python -m scripts.make_previews || echo "Previews were not made"; python -m scripts.make_peaks || echo "Waveforms were not made" ) &

# The API listens only inside the container; the site in front of it is the only way in.
# Proxy headers are trusted from the site process alone, so a visitor can't fake their address.
uvicorn allegro.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1 &
API_PID=$!

# If the API stops, stop the whole container so the hosting restarts it
( while kill -0 "$API_PID" 2>/dev/null; do sleep 5; done; echo "API exited, stopping the container"; kill 1 ) &

exec env HOST=0.0.0.0 NITRO_PORT="$PORT" NUXT_API_INTERNAL=http://127.0.0.1:8000 node /app/web/server/index.mjs
