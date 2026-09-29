"""Limits on repeated attempts (password guessing, invitation guessing, message floods).

In memory of this process: enough for one application instance. Several instances would need a shared
store (Redis) — the interface stays the same.
"""
import threading
import time

from allegro.core.errors import TooManyAttempts


def client_ip(request) -> str:
    """The visitor's address for the limits. On Render every request comes through Cloudflare, which puts the
    real address into CF-Connecting-IP (and replaces any such header a visitor sends); without it — the
    address uvicorn took from the proxy headers of the site's own server."""
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "")


class AttemptLimiter:
    def __init__(self, max_attempts: int, window_seconds: int, message: str = "Слишком много попыток. Попробуйте позже."):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self.message = message
        self._attempts: dict[tuple, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: tuple, now: float) -> list[float]:
        recent = [t for t in self._attempts.get(key, []) if now - t < self.window]
        if recent:
            self._attempts[key] = recent
        else:
            self._attempts.pop(key, None)
        return recent

    def check(self, key: tuple) -> None:
        """Raise if this key already used up its attempts"""
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) >= self.max_attempts:
                minutes = int(self.window - (now - recent[0])) // 60 + 1
                raise TooManyAttempts(f"{self.message} Через {minutes} мин.")

    def hit(self, key: tuple) -> None:
        with self._lock:
            self._attempts.setdefault(key, []).append(time.monotonic())

    def reset(self, key: tuple) -> None:
        with self._lock:
            self._attempts.pop(key, None)


class RequestLimiter:
    """Requests per client in a sliding minute: keeps one address from flooding the application.

    Generous for a person (nobody clicks «save» 120 times a minute), tight for a script.
    """

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if now - self._last_sweep > 300:  # forget clients that went quiet, so memory stays small
                self._hits = {c: t for c, t in self._hits.items() if t and now - t[-1] < 60}
                self._last_sweep = now
            recent = [t for t in self._hits.get(client, []) if now - t < 60]
            if len(recent) >= self.per_minute:
                self._hits[client] = recent
                return False
            recent.append(now)
            self._hits[client] = recent
            return True
