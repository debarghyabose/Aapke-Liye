from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as db:
        yield db


async def create_tables():
    """Development only. Production uses `alembic upgrade head`."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
