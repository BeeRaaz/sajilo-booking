from app.core.exceptions import InvalidCredentialsError
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
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
            logger.warning(f"Signup attempt with existing email: {email}")
            raise ValueError("User with this email already exists")

        # Hash the password
        password_hash = hash_password(password)

        # Create the user
        user = await self.user_repository.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
        )

        await self.user_repository.commit()

        logger.info(f"User created successfully: id={user.id}")
        return user

    async def login_user(
        self,
        email: str,
        password: str,
    ):
        # Check for existing user
        user = await self.user_repository.get_by_email(email)

        if not user or not verify_password(
            password=password, password_hash=user.password_hash
        ):
            logger.warning(f"Invalid login attempt for email: {email}")
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
