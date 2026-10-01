from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import UserRepository
from app.services import AuthService


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]):
    return UserRepository(session)


def get_auth_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
):
    return AuthService(repository)
