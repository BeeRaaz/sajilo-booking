import asyncio

import pytest
from sqlalchemy import select

from app.core.security import decode_token
from app.models import RefreshToken, User
from app.repositories import UserRepository


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


async def test_signup_duplicate_email_case_insensitive(client):
    signup_payload_first = {
        "first_name": "Test",
        "last_name": "User",
        "email": "Test@example.com",
        "password": "test-user-password@123",
    }

    signup_payload_second = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "test-user-password@123",
    }

    response_first = await client.post("/auth/signup", json=signup_payload_first)

    assert response_first.status_code == 201

    response_second = await client.post("/auth/signup", json=signup_payload_second)

    assert response_second.status_code == 409


@pytest.mark.parametrize(
    "password",
    ["", "a", "x" * 11, "x" * 129],
    ids=["empty", "one-char", "11-chars", "129-chars"],
)
async def test_signup_rejects_invalid_password_length(client, password):
    response = await client.post(
        "/auth/signup",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "badpassword@example.com",
            "password": password,
        },
    )

    assert response.status_code == 422
    # The error must point at the password field so the client can show it.
    assert response.json()["detail"][0]["loc"][-1] == "password"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("exactly12@example.com", "x" * 12),
        ("exactly128@example.com", "x" * 128),
    ],
    ids=["min-length", "max-length"],
)
async def test_signup_accepts_password_at_length_limits(client, email, password):
    response = await client.post(
        "/auth/signup",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201


async def test_login_does_not_apply_password_length_rules(client):
    # Length rules are for creating a password, not for checking one.
    response = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "short"},
    )

    assert response.status_code == 401


async def test_signup_duplicate_email_when_precheck_misses_it(client, monkeypatch):
    # Simulates the race: the "does this email exist?" check passes, but another
    # request inserted the same email before our insert. The unique constraint
    # then fails, and that must be a 409, not a 500.
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "racing@example.com",
        "password": "racing-user-password@123",
    }

    first = await client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    async def precheck_finds_nothing(self, user_email):
        return None

    monkeypatch.setattr(UserRepository, "get_by_email", precheck_finds_nothing)

    second = await client.post("/auth/signup", json=payload)

    assert second.status_code == 409
    assert second.json()["detail"] == "User with this email already exists"


async def test_signup_simultaneous_requests_create_one_user(client):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "simultaneous@example.com",
        "password": "simultaneous-password@123",
    }

    responses = await asyncio.gather(
        *(client.post("/auth/signup", json=payload) for _ in range(5))
    )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 409, 409, 409, 409]


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


async def test_login_mixed_case_email(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "tEsTmiXedCase@ExamplE.COM",
        "password": "a-strong-password123",
    }

    signup_response = await client.post("/auth/signup", json=signup_payload)

    assert signup_response.status_code == 201
    assert signup_response.json()["email"] == "testmixedcase@example.com"

    response = await client.post(
        "/auth/login",
        json={
            "email": "testmixedcase@example.com",
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_email_with_surrounding_whitespace(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "whitespace@example.com",
        "password": "a-strong-password123",
    }

    await client.post("/auth/signup", json=signup_payload)

    response = await client.post(
        "/auth/login",
        json={
            "email": "  whitespace@example.com  ",
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 200


async def test_login_non_string_email_returns_422(client):
    for bad_email in (None, 123):
        response = await client.post(
            "/auth/login",
            json={"email": bad_email, "password": "whatever"},
        )

        assert response.status_code == 422


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


async def test_logout_revokes_token(client, db_session):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "logoutrevoke@example.com",
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

    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert logout_response.status_code == 204

    payload = decode_token(refresh_token)
    stored = await db_session.execute(
        select(RefreshToken).where(RefreshToken.jti == payload["jti"])
    )
    token_row = stored.scalar_one()
    assert token_row.revoked is True


async def test_logout_twice_is_idempotent(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "logouttwice@example.com",
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

    refresh_token = login_response.json()["refresh_token"]

    first = await client.post(
        "/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )
    second = await client.post(
        "/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert first.status_code == 204
    assert second.status_code == 204


async def test_logout_with_wrong_token_still_succeeds(client):
    response = await client.post(
        "/auth/logout",
        json={
            "refresh_token": "this-is-not-a-real-jwt",
        },
    )
    assert response.status_code == 204


async def test_logout_then_refresh_fails(client):
    signup_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "logoutthenrefresh@example.com",
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

    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401
