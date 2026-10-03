import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, jti: str, expires_at: datetime.datetime):
        token = RefreshToken(
            user_id=user_id,
            jti=jti,
            expires_at=expires_at,
        )

        self.session.add(token)

        return token

    async def commit(self):
        await self.session.commit()
