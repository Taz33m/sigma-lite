"""Small in-process rate limiter for sensitive demo/API endpoints."""
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.request_context import client_ip_from_request
from app.core.security import decode_token
from app.services.audit import record_audit_event


AUTH_RATE_LIMIT = 20
AUTH_IDENTITY_RATE_LIMIT = 10
UPLOAD_USER_RATE_LIMIT = 10
UPLOAD_IP_RATE_LIMIT = 60
EXPORT_RATE_LIMIT = 10
QUERY_RATE_LIMIT = 300
CELL_EDIT_RATE_LIMIT = 120
FORMULA_PREVIEW_RATE_LIMIT = 60
MUTATION_RATE_LIMIT = 60
RATE_LIMIT_WINDOW_SECONDS = 60


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
_redis_client = None


def _get_redis_client():
    global _redis_client
    if settings.RATE_LIMIT_BACKEND == "memory":
        return None
    if settings.ENVIRONMENT.lower() in {"test", "testing"} and settings.RATE_LIMIT_BACKEND == "auto":
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        if settings.RATE_LIMIT_BACKEND == "redis":
            raise
        return None


def _rate_limit_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Please try again shortly.",
    )


def _check_redis_sliding_window(
    client,
    key: str,
    limit: int,
    window_seconds: int,
    *,
    now: Optional[float] = None,
) -> None:
    """Check a Redis-backed sliding window using a sorted set."""
    current_time = time.time() if now is None else now
    redis_key = f"sigmalite:rate:{key}"
    member = f"{current_time:.6f}:{uuid4().hex}"

    # Keep hits exactly on the boundary, matching the in-memory limiter's
    # "older than window" behavior.
    client.zremrangebyscore(redis_key, 0, current_time - window_seconds - 1e-9)
    client.zadd(redis_key, {member: current_time})
    client.expire(redis_key, window_seconds * 2)
    count = client.zcard(redis_key)
    if count > limit:
        client.zrem(redis_key, member)
        raise _rate_limit_exception()


def _check_with_fallback(key: str, limit: int, window_seconds: int) -> None:
    client = _get_redis_client()
    if not client:
        rate_limiter.check(key, limit, window_seconds)
        return

    _check_redis_sliding_window(client, key, limit, window_seconds)


def _client_key(request: Request, scope: str) -> str:
    actor_id = _actor_id_from_request(request)
    if scope in {"export", "query", "upload", "cell_edit", "formula_preview", "mutation"} and actor_id is not None:
        return f"{scope}:user:{actor_id}"
    return _ip_key(request, scope)


def _ip_key(request: Request, scope: str) -> str:
    host = client_ip_from_request(request) or "unknown"
    return f"{scope}:ip:{host}"


def _actor_id_from_request(request: Request) -> Optional[int]:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    payload = decode_token(header.split(" ", 1)[1])
    if not payload or payload.get("type") != "access":
        return None
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None


def _record_rate_limit_block(
    db: Session,
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    try:
        record_audit_event(
            db,
            "rate_limit.blocked",
            "request",
            actor_id=_actor_id_from_request(request),
            metadata={
                "scope": scope,
                "method": request.method,
                "path": request.url.path,
                "limit": limit,
                "window_seconds": window_seconds,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()


def _check_request_rate_limit(
    request: Request,
    db: Session,
    scope: str,
    limit: int,
    window_seconds: int,
    key: Optional[str] = None,
) -> None:
    try:
        _check_with_fallback(
            key or _client_key(request, scope),
            limit=limit,
            window_seconds=window_seconds,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            _record_rate_limit_block(db, request, scope, limit, window_seconds)
        raise


def check_auth_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "auth",
        limit=AUTH_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def check_auth_identity_rate_limit(
    request: Request,
    db: Session,
    identity: str,
) -> None:
    normalized_identity = identity.strip().lower() or "unknown"
    _check_request_rate_limit(
        request,
        db,
        "auth_identity",
        limit=AUTH_IDENTITY_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        key=f"auth:identity:{normalized_identity}",
    )


def check_upload_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "upload",
        limit=UPLOAD_USER_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
    _check_request_rate_limit(
        request,
        db,
        "upload_ip",
        limit=UPLOAD_IP_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        key=_ip_key(request, "upload_ip"),
    )


def check_export_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "export",
        limit=EXPORT_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def check_query_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "query",
        limit=QUERY_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def check_cell_edit_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "cell_edit",
        limit=CELL_EDIT_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def check_formula_preview_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "formula_preview",
        limit=FORMULA_PREVIEW_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )


def check_mutation_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _check_request_rate_limit(
        request,
        db,
        "mutation",
        limit=MUTATION_RATE_LIMIT,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
