def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data


def test_register_duplicate_email(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "user2",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "loginpass123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "loginuser", "password": "loginpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user_profile(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "profile@example.com",
            "username": "profileuser",
            "password": "profilepass123",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": "profileuser", "password": "profilepass123"},
    ).json()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "profileuser"


def test_refresh_token(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "refresh@example.com",
            "username": "refreshuser",
            "password": "refreshpass123",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": "refreshuser", "password": "refreshpass123"},
    ).json()

    response = client.post(
        "/api/auth/refresh",
        json={"token": login["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_token_rotation_blocks_reuse_and_revokes_family(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "rotate@example.com",
            "username": "rotateuser",
            "password": "rotatepass123",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": "rotateuser", "password": "rotatepass123"},
    ).json()

    refreshed = client.post(
        "/api/auth/refresh",
        json={"token": login["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text

    replay = client.post(
        "/api/auth/refresh",
        json={"token": login["refresh_token"]},
    )
    assert replay.status_code == 401

    family_revoked = client.post(
        "/api/auth/refresh",
        json={"token": refreshed.json()["refresh_token"]},
    )
    assert family_revoked.status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "logout@example.com",
            "username": "logoutuser",
            "password": "logoutpass123",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": "logoutuser", "password": "logoutpass123"},
    ).json()

    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"refresh_token": login["refresh_token"]},
    )
    assert logout.status_code == 204, logout.text

    refresh = client.post(
        "/api/auth/refresh",
        json={"token": login["refresh_token"]},
    )
    assert refresh.status_code == 401


def test_logout_all_sessions_revokes_active_refresh_tokens(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "logout-all@example.com",
            "username": "logoutall",
            "password": "logoutallpass123",
        },
    )
    first = client.post(
        "/api/auth/login",
        data={"username": "logoutall", "password": "logoutallpass123"},
    ).json()
    second = client.post(
        "/api/auth/login",
        data={"username": "logoutall", "password": "logoutallpass123"},
    ).json()

    logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {first['access_token']}"},
        json={"all_sessions": True},
    )
    assert logout.status_code == 204, logout.text

    assert client.post("/api/auth/refresh", json={"token": first["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/refresh", json={"token": second["refresh_token"]}).status_code == 401


def test_successful_auth_flows_are_audited(client):
    register = client.post(
        "/api/auth/register",
        headers={"x-request-id": "auth-register-request"},
        json={
            "email": "audit-auth@example.com",
            "username": "auditauth",
            "password": "auditpass123",
        },
    )
    assert register.status_code == 201, register.text
    user_id = register.json()["id"]

    login = client.post(
        "/api/auth/login",
        headers={"x-request-id": "auth-login-request"},
        data={"username": "auditauth", "password": "auditpass123"},
    )
    assert login.status_code == 200, login.text

    refresh = client.post(
        "/api/auth/refresh",
        headers={"x-request-id": "auth-refresh-request"},
        json={"token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200, refresh.text

    audit = client.get(
        f"/api/audit?entity_type=user&entity_id={user_id}",
        headers={"Authorization": f"Bearer {refresh.json()['access_token']}"},
    )
    assert audit.status_code == 200, audit.text
    by_action = {event["action"]: event for event in audit.json()}
    assert by_action["auth.registered"]["request_id"] == "auth-register-request"
    assert by_action["auth.login_succeeded"]["request_id"] == "auth-login-request"
    assert by_action["auth.refresh_succeeded"]["request_id"] == "auth-refresh-request"


def test_refresh_token_rejects_malformed_subject(client):
    from app.core.security import create_refresh_token

    token = create_refresh_token({"sub": "not-a-user-id"})
    response = client.post("/api/auth/refresh", json={"token": token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "wrongpass@example.com",
            "username": "wrongpassuser",
            "password": "correctpass123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "wrongpassuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_unauthenticated_request_rejected(client):
    response = client.get("/api/datasets")
    assert response.status_code == 401
