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


def _add_missing_columns(conn):
    """Development only: create_all never alters existing tables, so a dev database made
    before a new column was added would break. Add such columns (all are nullable)."""
    from sqlalchemy import inspect, text
    insp = inspect(conn)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing and col.nullable:
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} '
                                  f'{col.type.compile(conn.dialect)}'))


async def create_tables():
    """Development only. Production uses `alembic upgrade head`."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
