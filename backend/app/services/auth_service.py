from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models import RefreshToken
from app.repositories import UserRepository


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
    ):
        # Check if the user already exists
        existing_user = await self.repository.get_by_email(email)

        if existing_user:
            logger.warning(f"Signup attempt with existing email: {email}")
            raise ValueError("User with this email already exists")

        # Hash the password
        password_hash = hash_password(password)

        # Create the user
        user = await self.repository.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
        )

        await self.repository.commit()

        logger.info(f"User created successfully: id={user.id}")
        return user

    async def login_user(
        self,
        email: str,
        password: str,
    ):
        # Check for existing user
        user = await self.repository.get_by_email(email)

        if not user or not verify_password(
            password=password, password_hash=user.password_hash
        ):
            logger.warning("Invalid credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Grant jwt tokens
        at = create_access_token(user_id=user.id)
        rt = create_refresh_token(user_id=user.id)

        # Store the refresh token on the db
        refresh_token = RefreshToken(
            user_id=user.id,
            jti=rt.jti,
            expires_at=rt.expire,
        )

        self.repository.session.add(refresh_token)

        await self.repository.commit()

        logger.info(f"Created jwt tokens for the user: {user.id}")
        return at, rt
