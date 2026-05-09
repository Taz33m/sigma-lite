import pytest

from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter


def test_production_rejects_disable_auth(tmp_path):
    with pytest.raises(ValueError, match="DISABLE_AUTH"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="x" * 48,
            ENVIRONMENT="production",
            DISABLE_AUTH=True,
            UPLOAD_DIR=str(tmp_path),
        )


def test_production_rejects_weak_secret(tmp_path):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="change-me",
            ENVIRONMENT="production",
            UPLOAD_DIR=str(tmp_path),
        )


def test_production_rejects_wildcard_cors(tmp_path):
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="x" * 48,
            ENVIRONMENT="production",
            ALLOWED_ORIGINS="*",
            UPLOAD_DIR=str(tmp_path),
        )


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()
    limiter.check("key", limit=2, window_seconds=60)
    limiter.check("key", limit=2, window_seconds=60)

    with pytest.raises(Exception):
        limiter.check("key", limit=2, window_seconds=60)
