from types import SimpleNamespace

import pytest

from app.core import rate_limit as rate_limit_module
from app.core.config import Settings, settings
from app.core.rate_limit import InMemoryRateLimiter, _check_redis_sliding_window


class FakeRedis:
    def __init__(self):
        self.zsets = {}
        self.expirations = {}

    def zremrangebyscore(self, key, minimum, maximum):
        members = self.zsets.setdefault(key, {})
        removed = [
            member
            for member, score in members.items()
            if minimum <= score <= maximum
        ]
        for member in removed:
            del members[member]
        return len(removed)

    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)
        return len(mapping)

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def zcard(self, key):
        return len(self.zsets.get(key, {}))

    def zrem(self, key, member):
        return 1 if self.zsets.get(key, {}).pop(member, None) is not None else 0


class DummyDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _request(host="203.0.113.9"):
    return SimpleNamespace(
        headers={},
        client=SimpleNamespace(host=host),
        method="POST",
        url=SimpleNamespace(path="/api/datasets"),
    )


def test_production_rejects_disable_auth(tmp_path):
    with pytest.raises(ValueError, match="DISABLE_AUTH"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="x" * 48,
            ENVIRONMENT="production",
            DISABLE_AUTH=True,
            RATE_LIMIT_BACKEND="redis",
            UPLOAD_DIR=str(tmp_path),
        )


def test_production_rejects_weak_secret(tmp_path):
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="change-me",
            ENVIRONMENT="production",
            RATE_LIMIT_BACKEND="redis",
            UPLOAD_DIR=str(tmp_path),
        )


def test_production_rejects_wildcard_cors(tmp_path):
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="x" * 48,
            ENVIRONMENT="production",
            ALLOWED_ORIGINS="*",
            RATE_LIMIT_BACKEND="redis",
            UPLOAD_DIR=str(tmp_path),
        )


def test_production_requires_redis_rate_limit_backend(tmp_path):
    with pytest.raises(ValueError, match="RATE_LIMIT_BACKEND"):
        Settings(
            DATABASE_URL="sqlite:///prod.db",
            SECRET_KEY="x" * 48,
            ENVIRONMENT="production",
            RATE_LIMIT_BACKEND="auto",
            UPLOAD_DIR=str(tmp_path),
        )


def test_default_local_cors_includes_loopback_hosts(tmp_path):
    settings = Settings(
        DATABASE_URL="sqlite:///dev.db",
        SECRET_KEY="dev-secret-with-enough-entropy",
        ENVIRONMENT="development",
        UPLOAD_DIR=str(tmp_path),
    )

    assert "http://localhost:5173" in settings.ALLOWED_ORIGINS
    assert "http://127.0.0.1:5173" in settings.ALLOWED_ORIGINS


def test_api_docs_default_to_private_in_public_environments(tmp_path):
    production = Settings(
        DATABASE_URL="sqlite:///prod.db",
        SECRET_KEY="x" * 48,
        ENVIRONMENT="production",
        RATE_LIMIT_BACKEND="redis",
        UPLOAD_DIR=str(tmp_path / "prod"),
    )
    staging = Settings(
        DATABASE_URL="sqlite:///staging.db",
        SECRET_KEY="x" * 48,
        ENVIRONMENT="staging",
        RATE_LIMIT_BACKEND="redis",
        UPLOAD_DIR=str(tmp_path / "staging"),
    )
    local = Settings(
        DATABASE_URL="sqlite:///dev.db",
        SECRET_KEY="dev-secret-with-enough-entropy",
        ENVIRONMENT="development",
        UPLOAD_DIR=str(tmp_path / "dev"),
    )

    assert production.api_docs_enabled() is False
    assert staging.api_docs_enabled() is False
    assert local.api_docs_enabled() is True


def test_api_docs_can_be_explicitly_exposed_in_public_environment(tmp_path):
    settings = Settings(
        DATABASE_URL="sqlite:///prod.db",
        SECRET_KEY="x" * 48,
        ENVIRONMENT="production",
        EXPOSE_API_DOCS=True,
        RATE_LIMIT_BACKEND="redis",
        UPLOAD_DIR=str(tmp_path),
    )

    assert settings.api_docs_enabled() is True


def test_metrics_default_to_private_in_public_environments(tmp_path):
    production = Settings(
        DATABASE_URL="sqlite:///prod.db",
        SECRET_KEY="x" * 48,
        ENVIRONMENT="production",
        RATE_LIMIT_BACKEND="redis",
        UPLOAD_DIR=str(tmp_path / "prod"),
    )
    staging = Settings(
        DATABASE_URL="sqlite:///staging.db",
        SECRET_KEY="x" * 48,
        ENVIRONMENT="staging",
        RATE_LIMIT_BACKEND="redis",
        UPLOAD_DIR=str(tmp_path / "staging"),
    )
    local = Settings(
        DATABASE_URL="sqlite:///dev.db",
        SECRET_KEY="dev-secret-with-enough-entropy",
        ENVIRONMENT="development",
        UPLOAD_DIR=str(tmp_path / "dev"),
    )

    assert production.public_metrics_enabled() is False
    assert staging.public_metrics_enabled() is False
    assert local.public_metrics_enabled() is True


def test_metrics_endpoint_requires_token_in_public_environment(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "EXPOSE_PUBLIC_METRICS", False)
    monkeypatch.setattr(settings, "METRICS_TOKEN", "metrics-secret")

    missing = client.get("/metrics")
    assert missing.status_code == 401

    wrong = client.get("/metrics", headers={"x-metrics-token": "wrong"})
    assert wrong.status_code == 401

    allowed = client.get("/metrics", headers={"x-metrics-token": "metrics-secret"})
    assert allowed.status_code == 200
    assert "sigmalite_http_requests_total" in allowed.text


def test_metrics_endpoint_can_be_hidden_in_public_environment(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "EXPOSE_PUBLIC_METRICS", False)
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")

    response = client.get("/metrics")

    assert response.status_code == 404


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()
    limiter.check("key", limit=2, window_seconds=60)
    limiter.check("key", limit=2, window_seconds=60)

    with pytest.raises(Exception):
        limiter.check("key", limit=2, window_seconds=60)


def test_upload_rate_limiter_checks_user_and_ip_buckets(monkeypatch):
    rate_limit_module.rate_limiter.reset()
    events = []

    def fake_record_audit_event(db, action, entity_type, *args, **kwargs):
        events.append(
            {
                "action": action,
                "entity_type": entity_type,
                "metadata": kwargs["metadata"],
            }
        )

    monkeypatch.setattr(rate_limit_module, "_actor_id_from_request", lambda request: 7)
    monkeypatch.setattr(rate_limit_module, "UPLOAD_USER_RATE_LIMIT", 100)
    monkeypatch.setattr(rate_limit_module, "UPLOAD_IP_RATE_LIMIT", 2)
    monkeypatch.setattr(rate_limit_module, "record_audit_event", fake_record_audit_event)

    request = _request()
    db = DummyDb()

    rate_limit_module.check_upload_rate_limit(request, db)
    rate_limit_module.check_upload_rate_limit(request, db)
    with pytest.raises(Exception):
        rate_limit_module.check_upload_rate_limit(request, db)

    assert events[-1]["action"] == "rate_limit.blocked"
    assert events[-1]["entity_type"] == "request"
    assert events[-1]["metadata"]["scope"] == "upload_ip"
    assert events[-1]["metadata"]["limit"] == 2
    assert db.commits == 1


def test_redis_rate_limiter_uses_sliding_window():
    redis = FakeRedis()
    key = "query:user:1"
    redis_key = f"sigmalite:rate:{key}"

    _check_redis_sliding_window(redis, key, limit=2, window_seconds=60, now=100)
    _check_redis_sliding_window(redis, key, limit=2, window_seconds=60, now=101)

    with pytest.raises(Exception):
        _check_redis_sliding_window(redis, key, limit=2, window_seconds=60, now=160)

    assert redis.zcard(redis_key) == 2
    assert redis.expirations[redis_key] == 120

    _check_redis_sliding_window(redis, key, limit=2, window_seconds=60, now=161)

    assert redis.zcard(redis_key) == 2
