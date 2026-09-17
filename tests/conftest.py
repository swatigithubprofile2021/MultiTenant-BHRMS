import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.api.deps.auth_dep import get_redis, get_db
from app.core.config import settings
from app.main import app
from tests.mocks import DummyRedis
import tests.config as config


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def setup_dependency_overrides():
    # 1. Setup Phase
    app.dependency_overrides[get_redis] = lambda: DummyRedis()

    test_engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    TestSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        app.dependency_overrides[get_db] = lambda: session

        yield session

        app.dependency_overrides.clear()

    # Engine Cleanup
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_client(setup_dependency_overrides):
    # Use ASGITransport to wrap the app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client
        finally:
            await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def super_admin_token(async_client):
    """Login as super_admin and store token in global config"""
    if not config.SUPER_ADMIN_TOKEN:
        headers = {"Content-Type": "application/json"}
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": config.SUPER_ADMIN_EMAIL,
                "password": config.SUPER_ADMIN_PASSWORD,
            },
            headers=headers,
        )
        print(resp.text)
        assert resp.status_code == 200
        token = resp.headers["authorization"]
        config.SUPER_ADMIN_TOKEN = token
    return config.SUPER_ADMIN_TOKEN
