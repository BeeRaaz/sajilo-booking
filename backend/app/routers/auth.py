from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.exceptions import InvalidCredentialsError, InvalidTokenError
from app.deps import get_auth_service
from app.models import User
from app.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services import AuthService

auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@auth_router.post(
    "/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    try:
        return await service.create_user(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@auth_router.post(
    "/login", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
async def login(
    payload: UserLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        access_token, refresh_token = await service.login_user(
            email=payload.email,
            password=payload.password,
        )

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e

    return TokenResponse(
        access_token=access_token.token,
        refresh_token=refresh_token.token,
    )


@auth_router.post(
    "/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK
)
async def refresh(
    payload: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        access_token, refresh_token = await service.refresh_tokens(
            refresh_token=payload.refresh_token
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e

    return TokenResponse(
        access_token=access_token.token,
        refresh_token=refresh_token.token,
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> None:
    await service.logout_user(refresh_token=payload.refresh_token)
