"""Channel library queries — read-only access to imported channels and sources.

LibraryService wraps an async sessionmaker and provides listSources(),
listChannels() (optionally filtered by source), getChannel() by channel_id,
and searchChannels() with full-text-like ilike matching.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, M3USource

logger = logging.getLogger(__name__)


class LibraryService:
    def __init__(self):
        self._sm: async_sessionmaker[AsyncSession] = DatabaseManager.get_sessionmaker()

    async def getChannel(self, channel_id: str) -> Channel | None:
        async with self._sm() as session:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    async def listSources(self) -> list[M3USource]:
        async with self._sm() as session:
            stmt = select(M3USource).order_by(M3USource.id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def listChannels(self, source_id: int | None = None) -> list[Channel]:
        async with self._sm() as session:
            if source_id is not None:
                stmt = (
                    select(Channel)
                    .join(Channel.m3u_links)
                    .where(Channel.m3u_links.any(source_id=source_id))
                )
            else:
                stmt = select(Channel).order_by(Channel.display_name)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def searchChannels(self, query: str) -> list[Channel]:
        async with self._sm() as session:
            pattern = f"%{query}%"
            stmt = (
                select(Channel)
                .where(
                    Channel.display_name.ilike(pattern)
                    | Channel.channel_id.ilike(pattern)
                    | Channel.canonical_name.ilike(pattern)
                )
                .order_by(Channel.display_name)
                .limit(50)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
