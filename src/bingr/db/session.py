"""Async session factory — creates an async_sessionmaker bound to a SQLite DB.

The returned sessionmaker can be used as an async context manager
(async with sessionmaker() as session:) for all DB operations.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def createSessionmaker(dbPath: str | Path) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{dbPath}", echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
