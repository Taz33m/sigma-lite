"""Request-scoped helpers shared by logging, rate limits, and audit events."""

from fastapi import Request

from app.core.config import settings


def client_ip_from_request(request: Request | None) -> str | None:
    """Return a safe client IP, trusting proxy headers only when configured."""
    if not request:
        return None

    trusted_header = settings.TRUST_PROXY_CLIENT_IP_HEADER.strip().lower()
    if trusted_header:
        value = request.headers.get(trusted_header)
        if value:
            return value.split(",", 1)[0].strip()

    return request.client.host if request.client else None
