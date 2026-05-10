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
