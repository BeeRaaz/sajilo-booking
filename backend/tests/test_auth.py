from sqlalchemy import select

from app.models import RefreshToken, User


async def test_signup_sucess(client):
    response = await client.post(
        "/auth/signup",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "password": "test-user-password@123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert "password_hash" not in data


async def test_signup_duplicate_email(client):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "duplicate@example.com",
        "password": "duplicate-user-password@123",
    }

    first = await client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/signup", json=payload)
    assert second.status_code == 409


async def test_login_success(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "loginsuccess@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "loginwrong@example.com",
        "password": "correct-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


async def test_login_nonexistent_email(client):
    response = await client.post(
        "/auth/login",
        json={
            "email": "doesnotexist@example.com",
            "password": "whatever123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


async def test_login_creates_refresh_token_row(client, db_session):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "refreshcheck@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    assert response.status_code == 200

    user_result = await db_session.execute(
        select(User).where(User.email == signup_payload["email"])
    )
    user = user_result.scalar_one()

    token_result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    token = token_result.scalar_one_or_none()

    assert token is not None
    assert token.revoked is False


async def test_token_refresh_success(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "tokenrefreshcheck@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    login_response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": login_response.json()["refresh_token"],
        },
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_token_refresh_duplicate_token(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "tokenrefreshduplicate@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    login_response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    refresh_response_first = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": login_response.json()["refresh_token"],
        },
    )
    assert refresh_response_first.status_code == 200

    refresh_response_second = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": login_response.json()["refresh_token"],
        },
    )
    assert refresh_response_second.status_code == 401


async def test_token_refresh_wrong_token(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "tokenrefreshwrongtoken@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": "wrong-token-passed-here",
        },
    )

    assert refresh_response.status_code == 401


async def test_token_refresh_wrong_token_type(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "tokenrefreshwrongtype@example.com",
        "password": "a-strong-password123",
    }
    await client.post("/auth/signup", json=signup_payload)

    login_response = await client.post(
        "/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": login_response.json()["access_token"],
        },
    )

    assert refresh_response.status_code == 401
