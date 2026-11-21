import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import decode_token
from app.db import get_session
from app.models import User
from app.repositories import RefreshTokenRepository, UserRepository
from app.services import AuthService

# auto_error=False so a missing header is reported by us as a 401 (below),
# with the same response as every other authentication failure.
bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]):
    return UserRepository(session)


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return RefreshTokenRepository(session)


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_token_repository: Annotated[
        RefreshTokenRepository, Depends(get_refresh_token_repository)
    ],
):
    return AuthService(user_repository, refresh_token_repository)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Return the user for the bearer access token, or raise 401.

    Every failure gives the same response so a client can't tell why it failed.
    """
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials)
    except jwt.InvalidTokenError:  # also covers expired tokens
        logger.info("Rejected request with an invalid or expired access token")
        raise _unauthorized() from None

    # A refresh token must never work as an access token.
    if payload.get("type") != "access":
        logger.warning("Rejected request that used a non-access token")
        raise _unauthorized()

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        logger.warning("Rejected access token with a missing or malformed subject")
        raise _unauthorized() from None

    user = await user_repository.get_by_id(user_id)

    if user is None:
        logger.warning(f"Rejected access token for a missing user: id={user_id}")
        raise _unauthorized()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
