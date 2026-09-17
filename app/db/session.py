from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

#  Async Engine (for runtime)
ASYNC_DATABASE_URL = (
    settings.ASYNC_DATABASE_URL
)  # e.g. "postgresql+asyncpg://user:pass@host/db"

# Sync URL
SYNC_DATABASE_URL = settings.SYNC_DATABASE_URL

async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=10,
    pool_timeout=settings.DB_TIMEOUT,
    pool_pre_ping=True,
)

# Sync engine (Required by PGVectorStore)
engine: Engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=10,
    pool_timeout=settings.DB_TIMEOUT,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)

# Async Session Factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Dependency for FastAPI
async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
