"""Small in-process rate limiter for sensitive demo/API endpoints."""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Sliding-window IP limiter.

    This is intentionally single-process. It protects the local/demo app from
    accidental abuse and is not a substitute for a distributed production WAF.
    """

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        hits = self._hits[key]

        while hits and now - hits[0] > window_seconds:
            hits.popleft()

        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
            )

        hits.append(now)


rate_limiter = InMemoryRateLimiter()


def _client_key(request: Request, scope: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{scope}:{host}"


def check_auth_rate_limit(request: Request) -> None:
    rate_limiter.check(_client_key(request, "auth"), limit=120, window_seconds=60)


def check_upload_rate_limit(request: Request) -> None:
    rate_limiter.check(_client_key(request, "upload"), limit=60, window_seconds=60)
