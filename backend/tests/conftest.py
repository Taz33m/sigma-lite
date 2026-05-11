"""Shared pytest fixtures for the backend test suite."""
import os
import sys
from pathlib import Path

# Provide required settings before importing the app, so pydantic_settings
# does not fail when no .env file exists in the test environment.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sigmalite.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DISABLE_AUTH", "False")
os.environ.setdefault("ENVIRONMENT", "test")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.rate_limit import rate_limiter


def _use_configured_database_url() -> bool:
    return settings.DATABASE_URL.startswith(("postgresql://", "postgresql+"))


def _reset_redis_rate_limits() -> None:
    if settings.ENVIRONMENT.lower() not in {"test", "testing"}:
        return
    if settings.RATE_LIMIT_BACKEND != "redis":
        return

    import redis

    client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    keys = list(client.scan_iter("sigmalite:rate:*"))
    if keys:
        client.delete(*keys)


@pytest.fixture(scope="session")
def engine():
    if _use_configured_database_url():
        eng = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    else:
        eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    rate_limiter.reset()
    _reset_redis_rate_limits()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, username: str, email: str, password: str = "testpass123"):
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_token(client):
    return _register_and_login(client, "fixtureuser", "fixture@example.com")


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def second_user_headers(client):
    token = _register_and_login(client, "otheruser", "other@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_csv_bytes():
    return b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCarol,40,SF\n"


@pytest.fixture
def uploaded_dataset(client, auth_headers, sample_csv_bytes):
    response = client.post(
        "/api/datasets",
        headers=auth_headers,
        data={"name": "test dataset", "description": "test"},
        files={"file": ("data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def created_sheet(client, auth_headers, uploaded_dataset):
    response = client.post(
        "/api/sheets",
        headers=auth_headers,
        json={
            "name": "test sheet",
            "description": "sheet for tests",
            "dataset_id": uploaded_dataset["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
