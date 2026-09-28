"""Limits on repeated attempts (password guessing, invitation guessing, message floods).

In memory of this process: enough for one application instance. Several instances would need a shared
store (Redis) — the interface stays the same.
"""
import threading
import time

from allegro.core.errors import TooManyAttempts


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
