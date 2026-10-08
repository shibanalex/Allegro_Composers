#!/bin/sh
# Container entrypoint (see Dockerfile): update the database schema, start the API, the chat's
# WebSocket server and the site, then the gateway in front of them.
set -e

cd /app/backend
alembic upgrade head
# Light copies of pictures that don't have one yet (idempotent; in the background, the site doesn't wait)
( python -m scripts.make_previews || echo "Previews were not made"; python -m scripts.make_peaks || echo "Waveforms were not made" ) &

# The API listens only inside the container; the site in front of it is the only way in.
# Proxy headers are trusted from the site process alone, so a visitor can't fake their address.
uvicorn allegro.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1 &
API_PID=$!

# The chat's WebSocket server (Centrifugo): its secrets are derived from SECRET_KEY by the API's own code,
# so nothing new is configured. Only the API publishes; browsers listen. Restarted if it ever stops —
# the site works without it, the chat is just not live meanwhile.
eval "$(python -m allegro.core.realtime)"
( while true; do centrifugo --config /app/deploy/centrifugo.json; echo "Centrifugo exited, restarting"; sleep 3; done ) &

# The site (Nuxt) behind the gateway
env HOST=127.0.0.1 NITRO_PORT=3001 NUXT_API_INTERNAL=http://127.0.0.1:8000 node /app/web/server/index.mjs &
WEB_PID=$!

# If the API or the site stops, stop the whole container so the hosting restarts it
( while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do sleep 5; done
  echo "API or site exited, stopping the container"; kill 1 ) &

# The gateway on the public port: /connection → Centrifugo, everything else → the site
exec caddy run --config /app/deploy/Caddyfile --adapter caddyfile
