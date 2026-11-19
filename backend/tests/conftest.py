import asyncio
import os
from pathlib import Path

os.environ["ENVIRONMENT"] = "test"

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from alembic import command
from app.db import SessionLocal, engine
from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


async def _reset_schema() -> None:
    """Wipe everything (tables, enums, alembic_version) from the test database."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _upgrade_to_head() -> None:
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    # Build the schema with the real migrations, like production does.
    await _reset_schema()
    # alembic's env.py starts its own event loop, which cannot run inside
    # this already-running one, so run it in a worker thread.
    await asyncio.to_thread(_upgrade_to_head)
    yield
    await _reset_schema()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session
