import datetime
import uuid

import jwt
import pytest
from sqlalchemy import delete

from app.core import settings
from app.core.security import ALGORITHM
from app.models import User


async def _signup_and_login(client, email: str) -> dict:
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": "current-user-password@123",
    }
    signup = await client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    login = await client.post(
        "/auth/login", json={"email": email, "password": payload["password"]}
    )
    assert login.status_code == 200

    return {"user": signup.json(), "tokens": login.json()}


def _make_token(
    user_id: str,
    token_type: str = "access",
    expires_in: datetime.timedelta = datetime.timedelta(minutes=5),
    secret: str | None = None,
) -> str:
    now = datetime.datetime.now(datetime.UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "jti": str(uuid.uuid4()),
            "type": token_type,
            "iat": now,
            "exp": now + expires_in,
        },
        secret or settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=ALGORITHM,
    )


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_me_returns_current_user(client):
    data = await _signup_and_login(client, "me@example.com")

    response = await client.get(
        "/auth/me", headers=_bearer(data["tokens"]["access_token"])
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == data["user"]["id"]
    assert body["email"] == "me@example.com"
    assert "password_hash" not in body
    assert "password" not in body


async def test_me_without_authorization_header_returns_401(client):
    response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_garbage_token_returns_401(client):
    response = await client.get("/auth/me", headers=_bearer("not.a.jwt"))

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_wrong_auth_scheme_returns_401(client):
    response = await client.get(
        "/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )

    assert response.status_code == 401


async def test_me_with_expired_token_returns_401(client):
    data = await _signup_and_login(client, "expired@example.com")
    expired = _make_token(data["user"]["id"], expires_in=datetime.timedelta(minutes=-1))

    response = await client.get("/auth/me", headers=_bearer(expired))

    assert response.status_code == 401


async def test_me_with_token_signed_by_someone_else_returns_401(client):
    data = await _signup_and_login(client, "forged@example.com")
    forged = _make_token(
        data["user"]["id"], secret="not-the-real-secret-key-0123456789"
    )

    response = await client.get("/auth/me", headers=_bearer(forged))

    assert response.status_code == 401


async def test_me_rejects_refresh_token_used_as_access_token(client):
    data = await _signup_and_login(client, "refreshasaccess@example.com")

    response = await client.get(
        "/auth/me", headers=_bearer(data["tokens"]["refresh_token"])
    )

    assert response.status_code == 401


async def test_me_for_a_user_that_no_longer_exists_returns_401(client, db_session):
    data = await _signup_and_login(client, "deleted@example.com")
    await db_session.execute(
        delete(User).where(User.id == uuid.UUID(data["user"]["id"]))
    )
    await db_session.commit()

    response = await client.get(
        "/auth/me", headers=_bearer(data["tokens"]["access_token"])
    )

    assert response.status_code == 401


@pytest.mark.parametrize("subject", ["not-a-uuid", "", "12345"])
async def test_me_with_malformed_subject_returns_401(client, subject):
    response = await client.get("/auth/me", headers=_bearer(_make_token(subject)))

    assert response.status_code == 401


async def test_me_with_token_without_subject_returns_401(client):
    now = datetime.datetime.now(datetime.UTC)
    token = jwt.encode(
        {"type": "access", "iat": now, "exp": now + datetime.timedelta(minutes=5)},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=ALGORITHM,
    )

    response = await client.get("/auth/me", headers=_bearer(token))

    assert response.status_code == 401
