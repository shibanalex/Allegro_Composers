"""Real-time delivery through Centrifugo: the site's own WebSocket server, next to the API in the container.

The API stays the only writer: a message is saved in the database first, then published to a channel
through Centrifugo's HTTP API; browsers only listen (subscribe), they never publish themselves. So
Centrifugo holds nothing that matters; if it is down, nothing is lost, the page just isn't live.

- a browser connects with a token from the API (a JWT signed with CLIENT_SECRET): a member's carries
  their id, a guest's an empty subject (an anonymous listener);
- both secrets are derived from SECRET_KEY, like the push keys, so nothing new has to be configured:
  start.sh runs `python -m allegro.core.realtime` to hand them to Centrifugo.
"""
import hashlib
import hmac
import logging
import time
from typing import Any, Optional

import httpx
import jwt

from allegro.core.config import settings

log = logging.getLogger("allegro.realtime")

TOKEN_TTL = 12 * 3600  # s; the browser asks the API for a new one when it runs out


def _secret(label: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"allegro:centrifugo:{label}".encode(), hashlib.sha256).hexdigest()


def client_secret() -> str:
    return _secret("client-token")


def api_key() -> str:
    return _secret("http-api")


def allowed_origins() -> list[str]:
    """The site's own addresses: only its pages may open the WebSocket (no other site can listen in for a visitor)"""
    found = [settings.public_url, settings.site_url, settings.render_external_url]
    return list(dict.fromkeys(o.rstrip("/") for o in found if o))


def connection_token(user_id: Optional[str]) -> str:
    """A browser's pass to the WebSocket: a member by id, a guest anonymous (empty subject)"""
    now = int(time.time())
    return jwt.encode({"sub": user_id or "", "iat": now, "exp": now + TOKEN_TTL}, client_secret(), algorithm="HS256")


def publish(channel: str, data: dict[str, Any]) -> bool:
    """Send to everyone listening on the channel; never raises (the page simply isn't live without it)"""
    if not settings.centrifugo_api_url:
        return False
    try:
        r = httpx.post(f"{settings.centrifugo_api_url.rstrip('/')}/api/publish",
                       json={"channel": channel, "data": data}, headers={"X-API-Key": api_key()}, timeout=3)
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning("publish to %s failed: %s", channel, e)
        return False


if __name__ == "__main__":
    # For start.sh: the environment Centrifugo reads its secrets from
    print(f"export CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY={client_secret()}")
    print(f"export CENTRIFUGO_HTTP_API_KEY={api_key()}")
    print(f"export CENTRIFUGO_CLIENT_ALLOWED_ORIGINS='{' '.join(allowed_origins())}'")
