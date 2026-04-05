from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = settings.database_url

if settings.use_sqlite_fallback and "postgresql" in database_url:
    # Keep local startup reliable even in synced folders that reject SQLite file I/O.
    database_url = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(database_url, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
