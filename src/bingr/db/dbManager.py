"""Central engine + sessionmaker lifecycle — initialised once at app startup."""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from bingr.db.migrate import runMigrations

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton-managed ``AsyncEngine`` + ``async_sessionmaker``.

    **One-time initialisation** at app startup (or test fixture setup).
    After that, any service can call ``get_sessionmaker()`` to obtain the
    shared session factory — each ``async with get_sessionmaker() as session``
    yields a **fresh** ``AsyncSession``, safe for concurrent tasks.

    Usage::

        DatabaseManager.initialize("/path/to/db.sqlite")
        sm = DatabaseManager.get_sessionmaker()
        async with sm() as session:
            ...
    """

    _engine: AsyncEngine | None = None
    _sessionmaker: async_sessionmaker[AsyncSession] | None = None

    # ── lifecycle ────────────────────────────────────────────────

    @classmethod
    def initialize(
        cls,
        dbPath: str | Path,
        alembicIniPath: str | Path | None = None,
    ) -> None:
        """Run pending migrations, create engine, and create sessionmaker.

        Safe to call multiple times — any existing engine is disposed first.
        """
        cls.shutdownSync()
        runMigrations(dbPath, alembicIniPath)
        cls._engine = create_async_engine(
            f"sqlite+aiosqlite:///{dbPath}",
            echo=False,
            poolclass=NullPool,
        )
        cls._sessionmaker = async_sessionmaker(
            cls._engine,
            expire_on_commit=False,
        )
        logger.info("DatabaseManager initialised: %s", dbPath)

    # ── accessors ────────────────────────────────────────────────

    @classmethod
    def get_sessionmaker(cls) -> async_sessionmaker[AsyncSession]:
        """Return the shared session factory.

        Raises ``RuntimeError`` if ``initialize()`` has not been called.
        """
        if cls._sessionmaker is None:
            raise RuntimeError(
                "DatabaseManager not initialised - call initialize() first",
            )
        return cls._sessionmaker

    # ── shutdown ─────────────────────────────────────────────────

    @classmethod
    async def shutdown(cls) -> None:
        """Dispose the connection pool (async — use in clean shutdown paths)."""
        if cls._engine is not None:
            logger.info("DatabaseManager: disposing engine …")
            await cls._engine.dispose()
            cls._engine = None
            cls._sessionmaker = None

    @classmethod
    def shutdownSync(cls) -> None:
        """Dispose the connection pool synchronously (for ``atexit``)."""
        if cls._engine is not None:
            cls._engine.sync_engine.dispose()
            cls._engine = None
            cls._sessionmaker = None
