import os

# Test env must be set before any app import.
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
# Catalog writes are admin-only; in tests EVERY registered user is admin so
# existing helpers (create_language, POST /study-items) keep working.
os.environ.setdefault("ADMIN_EMAILS", "*")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models import Base

limiter.enabled = False  # rate limits are unit-tested separately, not here


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


async def register_and_login(client: AsyncClient, email: str) -> dict:
    """Returns Authorization headers for a fresh user."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": "sup3rsecret", "displayName": "Test"},
    )
    res = await client.post("/auth/login", json={"email": email, "password": "sup3rsecret"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['accessToken']}"}


async def create_language(client: AsyncClient, headers: dict, code="zh", name="Chinese") -> dict:
    res = await client.post(
        "/languages",
        json={"code": code, "name": name, "ttsLang": f"{code}-XX"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()
