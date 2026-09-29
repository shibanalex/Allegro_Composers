"""Web Push: notifications that appear on a phone or a computer even when the site is closed.

The site signs its pushes with a VAPID key pair. The pair is derived from SECRET_KEY, so nothing new has to
be configured or stored; a new SECRET_KEY means new keys (and browsers subscribe again, as they would
after signing in again anyway).

Pushes go only to the push services of the browsers themselves: a subscription's address is where the
server sends a request, so an address of any other host is refused (no server-side request forgery).
"""
import base64
import json
import logging
from functools import lru_cache
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from allegro.core.config import settings

log = logging.getLogger("allegro.push")

# The push services of Chrome/Edge/Opera/Yandex (FCM), Firefox, Safari and Windows
PUSH_HOSTS = ("fcm.googleapis.com", "push.services.mozilla.com", "push.apple.com", "notify.windows.com")
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def allowed_endpoint(endpoint: str) -> bool:
    url = urlparse(endpoint)
    host = (url.hostname or "").lower()
    return url.scheme == "https" and any(host == h or host.endswith("." + h) for h in PUSH_HOSTS)


@lru_cache(maxsize=1)
def _private_key() -> ec.EllipticCurvePrivateKey:
    seed = HKDF(algorithm=hashes.SHA256(), length=40, salt=b"allegro", info=b"web-push vapid key").derive(
        settings.secret_key.encode()
    )
    value = int.from_bytes(seed, "big") % (P256_ORDER - 1) + 1
    return ec.derive_private_key(value, ec.SECP256R1())


def public_key() -> str:
    """For the browser's pushManager.subscribe({applicationServerKey})"""
    raw = _private_key().public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Gone(Exception):
    """The browser has dropped this subscription: forget it"""


def send(endpoint: str, p256dh: str, auth: str, message: dict) -> None:
    """Blocking (an HTTPS request): call it from the worker"""
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush

    if not allowed_endpoint(endpoint):
        raise Gone("not a push service")
    pem = _private_key().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    subject = f"mailto:{settings.mail_from or settings.smtp_user}" if (settings.mail_from or settings.smtp_user) else "https://allegro.example"
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(message, ensure_ascii=False),
            vapid_private_key=Vapid.from_pem(pem),
            vapid_claims={"sub": subject},
            ttl=24 * 3600,
            timeout=10,
        )
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            raise Gone(str(status)) from e
        raise
