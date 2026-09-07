"""Watch session tracking — save sessions and query channel watch history.

Each playback occurrence is persisted as its own row in ``watch_sessions``.
Queries that power the home screen aggregate those rows:

- ``getContinueWatchingChannels()`` — distinct channels ordered by most-recent
  session (drives "Continue watching").
- ``getTopChannelsByWatchTime()`` — channels ranked by accumulated duration
  (drives "Top views overall").
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, WatchSession
from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.ui_models.channelDataModel import ChannelDataModel

if TYPE_CHECKING:
    from bingr.services.channelsManagementService import (
        ChannelsManagementService as ChannelsManagementServiceType,
    )
else:
    ChannelsManagementServiceType = "ChannelsManagementService"

logger = logging.getLogger(__name__)


class WatchSessionService:
    def __init__(self) -> None:
        self._sm: async_sessionmaker[AsyncSession] = DatabaseManager.get_sessionmaker()
        self._channelsService: ChannelsManagementServiceType = ChannelsManagementService()

    async def recordSession(
        self,
        channelPk: int,
        startedAt: str,
        endedAt: str,
        durationSeconds: int,
        completed: bool = False,
    ) -> WatchSession:
        """Persist a single watch session for a channel.

        Args:
            channelPk: Primary key of the channel that was watched.
            startedAt: ISO8601 UTC timestamp when playback began.
            endedAt: ISO8601 UTC timestamp when playback ended.
            durationSeconds: Wall-clock duration of the session in seconds.
            completed: True if playback reached a natural end.

        Returns:
            The persisted ``WatchSession`` row.
        """
        async with self._sm() as session:
            ws = WatchSession(
                channel_id=channelPk,
                started_at=startedAt,
                ended_at=endedAt,
                duration_seconds=durationSeconds,
                completed=completed,
            )
            session.add(ws)
            await session.commit()
            await session.refresh(ws)
            return ws

    async def getContinueWatchingChannels(self, limit: int = 15) -> list[ChannelDataModel]:
        """Return distinct channels ordered by most-recent watch session.

        Uses the latest ``ended_at`` per channel and orders by it descending,
        so the most recently watched channels come first. Unwatched channels
        (no session rows) are excluded. Feeds are eagerly loaded and each row
        is mapped to a :class:`ChannelDataModel`.
        """
        latestPerChannel = (
            select(
                WatchSession.channel_id,
                func.max(WatchSession.ended_at).label("last_watched"),
            )
            .group_by(WatchSession.channel_id)
            .subquery()
        )
        stmt = (
            select(Channel)
            .join(latestPerChannel, Channel.id == latestPerChannel.c.channel_id)
            .options(selectinload(Channel.feeds))
            .order_by(latestPerChannel.c.last_watched.desc())
            .limit(limit)
        )
        async with self._sm() as session:
            result = await session.execute(stmt)
            channels = list(result.scalars().unique().all())
        return [self._channelsService.mapChannel(c) for c in channels]

    async def getTopChannelsByWatchTime(self, limit: int = 10) -> list[tuple[Channel, int]]:
        """Return channels ranked by total accumulated watch time.

        Each row is a ``(Channel, total_seconds)`` tuple, ordered by total
        watch duration descending.
        """
        totalsPerChannel = (
            select(
                WatchSession.channel_id,
                func.sum(WatchSession.duration_seconds).label("total_seconds"),
            )
            .group_by(WatchSession.channel_id)
            .subquery()
        )
        stmt = (
            select(Channel, totalsPerChannel.c.total_seconds)
            .join(totalsPerChannel, Channel.id == totalsPerChannel.c.channel_id)
            .order_by(totalsPerChannel.c.total_seconds.desc())
            .limit(limit)
        )
        async with self._sm() as session:
            result = await session.execute(stmt)
            return list(result.all())

    async def countSessions(self) -> int:
        """Return the total number of recorded watch sessions."""
        stmt = select(func.count()).select_from(WatchSession)
        async with self._sm() as session:
            return (await session.execute(stmt)).scalar_one()
