from app.core.logging import logger
from app.core.security import hash_password
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
