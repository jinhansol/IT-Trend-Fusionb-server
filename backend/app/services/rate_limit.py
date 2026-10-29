"""In-process limiter for failed login attempts.

Limitation: counts are kept per process. With several workers each keeps its
own count; replace with a shared store (DB or proxy) before scaling out.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

_MAX_TRACKED_KEYS = 10_000


class FailedAttemptLimiter:
    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int | None:
        """Seconds until another attempt is allowed, or None if allowed now."""
        with self._lock:
            failures = self._recent_failures(key)
            if len(failures) < self.max_attempts:
                return None
            wait = failures[0] + self.window_seconds - self._clock()
            return max(1, math.ceil(wait))

    def record(self, key: str) -> None:
        """Count one attempt (for limits on every attempt, not only failures)."""
        self.record_failure(key)

    def record_failure(self, key: str) -> None:
        with self._lock:
            if len(self._failures) >= _MAX_TRACKED_KEYS:
                self._prune()
            self._recent_failures(key).append(self._clock())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _recent_failures(self, key: str) -> deque[float]:
        failures = self._failures.setdefault(key, deque())
        cutoff = self._clock() - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures

    def _prune(self) -> None:
        for key in list(self._failures):
            if not self._recent_failures(key):
                del self._failures[key]
