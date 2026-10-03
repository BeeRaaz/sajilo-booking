from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import RefreshTokenRepository, UserRepository
from app.services import AuthService


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
