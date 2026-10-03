import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID):
        user = await self.session.execute(select(User).where(User.id == user_id))

        return user.scalar_one_or_none()

    async def get_by_email(self, user_email: str):
        user = await self.session.execute(select(User).where(User.email == user_email))

        return user.scalar_one_or_none()

    async def create(
        self, first_name: str, last_name: str, email: str, password_hash: str
    ):
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
        )

        self.session.add(user)

        return user

    async def commit(self):
        await self.session.commit()
