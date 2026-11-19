import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr


def _normalize_email(value: Any) -> Any:
    # Only touch strings. Anything else (None, numbers, ...) is passed through
    # so pydantic reports a normal 422 validation error instead of crashing.
    if isinstance(value, str):
        return value.strip().lower()
    return value


NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: NormalizedEmail
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: NormalizedEmail
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
