import datetime
import uuid
from dataclasses import dataclass

import argon2
import jwt
from argon2 import PasswordHasher

from app.core import settings

ph = PasswordHasher()

ALGORITHM = "HS256"


@dataclass
class TokenClass:
    token: str
    jti: str
    expire: datetime.datetime


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except argon2.exceptions.VerifyMismatchError:
        return False


def _create_token(
    user_id: uuid.UUID, token_type: str, expires_delta: datetime.timedelta
) -> TokenClass:
    now = datetime.datetime.now(datetime.UTC)
    expire = now + expires_delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=ALGORITHM,
    )

    return TokenClass(
        token=token,
        jti=jti,
        expire=expire,
    )


def create_access_token(
    user_id: uuid.UUID,
) -> TokenClass:
    return _create_token(
        user_id,
        "access",
        datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    user_id: uuid.UUID,
) -> TokenClass:
    return _create_token(
        user_id,
        "refresh",
        datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    try:
        decoded_token = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
        )

        return decoded_token

    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")

    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Invalid token")
