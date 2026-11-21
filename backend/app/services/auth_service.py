import uuid

import jwt
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import InvalidCredentialsError, InvalidTokenError
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories import (
    RefreshTokenRepository,
    UserRepository,
)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
    ):
        # Check if the user already exists
        existing_user = await self.user_repository.get_by_email(email)

        if existing_user:
            logger.warning(
                f"Signup attempt with an already registered email: "
                f"existing user id={existing_user.id}"
            )
            raise ValueError("User with this email already exists")

        # Hash the password
        password_hash = hash_password(password)

        # Create the user. The check above is only a fast path: two simultaneous
        # signups can both pass it, so the unique constraint on users.email is
        # the real guard and we must handle it failing here.
        try:
            user = await self.user_repository.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=password_hash,
            )
            await self.user_repository.commit()
        except IntegrityError as e:
            await self.user_repository.rollback()
            logger.warning("Signup lost a race on an already registered email")
            raise ValueError("User with this email already exists") from e

        logger.info(f"User created successfully: id={user.id}")
        return user

    async def login_user(
        self,
        email: str,
        password: str,
    ):
        # Check for existing user
        user = await self.user_repository.get_by_email(email)

        if not user:
            logger.warning("Login attempt for an unknown account")
            raise InvalidCredentialsError("Invalid credentials")

        if not verify_password(password=password, password_hash=user.password_hash):
            logger.warning(f"Login attempt with a wrong password: user id={user.id}")
            raise InvalidCredentialsError("Invalid credentials")

        # Grant jwt tokens
        at = create_access_token(user_id=user.id)
        rt = create_refresh_token(user_id=user.id)

        # Store the refresh token on the db
        await self.refresh_token_repository.create(
            user_id=user.id,
            jti=rt.jti,
            expires_at=rt.expire,
        )

        await self.refresh_token_repository.commit()

        logger.info(f"Created jwt tokens for the user: {user.id}")
        return at, rt

    async def refresh_tokens(self, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            logger.warning("Refresh attempted with invalid or expired token")
            raise InvalidTokenError("Invalid or expired refresh token") from e

        if payload.get("type") != "refresh":
            logger.warning("Refresh attempted with a non-refresh token")
            raise InvalidTokenError("Invalid or expired refresh token")

        stored_token = await self.refresh_token_repository.get_by_jti(payload["jti"])

        if not stored_token or stored_token.revoked:
            logger.warning(
                f"Refresh attempted with unknown or revoked jti: {payload['jti']}"
            )
            raise InvalidTokenError("Invalid or expired refresh token")

        # Rotate: kill the old token
        stored_token.revoked = True

        user_id = uuid.UUID(payload["sub"])
        at = create_access_token(user_id=user_id)
        rt = create_refresh_token(user_id=user_id)

        await self.refresh_token_repository.create(
            user_id=user_id,
            jti=rt.jti,
            expires_at=rt.expire,
        )
        await self.refresh_token_repository.commit()

        logger.info(f"Rotated refresh token for user: {user_id}")

        return at, rt

    async def logout_user(self, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            logger.info(
                "Logout attempted with an invalid or expired token; "
                "already effectively logged out"
            )
            return

        if payload.get("type") != "refresh":
            logger.warning("Logout attempted with a non-refresh token; ignoring")
            return

        stored_token = await self.refresh_token_repository.get_by_jti(
            jti=payload["jti"]
        )

        if not stored_token or stored_token.revoked:
            logger.info(
                f"Logout attempted for unknown or already-revoked jti: {payload['jti']}"
            )
            return

        # Kill the stored_token
        stored_token.revoked = True
        await self.refresh_token_repository.commit()

        logger.info(f"Logged out user, revoked jti: {payload['jti']}")
