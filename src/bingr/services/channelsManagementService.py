from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import exists, func, or_, select, true
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.selectable import Select

from bingr.common.commonUtils import normalizeUrl
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, Feed
from bingr.ui_models.channelDataModel import ChannelDataModel
from bingr.ui_models.streamModel import StreamModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_RESOLUTION_TO_QUALITY: dict[int, str] = {
    240: "SD",
    360: "SD",
    480: "SD",
    540: "SD",
    576: "SD",
    720: "HD",
    1080: "FHD",
    1440: "QHD",
    2160: "4K",
    4320: "8K",
}

_FORMAT_TO_RESOLUTION: dict[str, str] = {
    "SD": "480i",
    "HD": "720p",
    "FHD": "1080p",
    "QHD": "1440p",
    "4K": "2160p",
    "UHD": "2160p",
    "8K": "4320p",
}

_QUALITY_TO_FORMATS: dict[str, list[str]] = {
    "SD": ["480i", "576i"],
    "HD": ["720p", "720i"],
    "FHD": ["1080p", "1080i"],
    "QHD": ["1440p"],
    "4K": ["2160p"],
    "8K": ["4320p"],
}

# ISO 639-2 (3-letter) to ISO 639-1 (2-letter) code map.
_I639_2_TO_1: dict[str, str] = {
    "aar": "aa",
    "abk": "ab",
    "afr": "af",
    "amh": "am",
    "ara": "ar",
    "asm": "as",
    "aze": "az",
    "bak": "ba",
    "bel": "be",
    "ben": "bn",
    "bos": "bs",
    "bul": "bg",
    "cat": "ca",
    "ces": "cs",
    "chi": "zh",
    "dan": "da",
    "deu": "de",
    "dut": "nl",
    "ell": "el",
    "eng": "en",
    "epo": "eo",
    "est": "et",
    "eus": "eu",
    "fas": "fa",
    "fin": "fi",
    "fra": "fr",
    "fre": "fr",
    "gla": "gd",
    "gle": "ga",
    "glg": "gl",
    "gre": "el",
    "guj": "gu",
    "hat": "ht",
    "heb": "he",
    "hin": "hi",
    "hrv": "hr",
    "hun": "hu",
    "hye": "hy",
    "ind": "id",
    "isl": "is",
    "ita": "it",
    "jpn": "ja",
    "kan": "kn",
    "kat": "ka",
    "kaz": "kk",
    "khm": "km",
    "kor": "ko",
    "kur": "ku",
    "lat": "la",
    "lav": "lv",
    "lit": "lt",
    "ltz": "lb",
    "mal": "ml",
    "mar": "mr",
    "mkd": "mk",
    "mlt": "mt",
    "mon": "mn",
    "msa": "ms",
    "mya": "my",
    "nep": "ne",
    "nld": "nl",
    "nor": "no",
    "pan": "pa",
    "pol": "pl",
    "por": "pt",
    "pus": "ps",
    "ron": "ro",
    "rum": "ro",
    "rus": "ru",
    "san": "sa",
    "sin": "si",
    "slk": "sk",
    "slo": "sk",
    "slv": "sl",
    "snd": "sd",
    "sqi": "sq",
    "srp": "sr",
    "swa": "sw",
    "swe": "sv",
    "tam": "ta",
    "tel": "te",
    "tgk": "tg",
    "tha": "th",
    "tur": "tr",
    "ukr": "uk",
    "urd": "ur",
    "uzb": "uz",
    "vie": "vi",
    "yid": "yi",
    "zho": "zh",
    "spa": "es",
}


class ChannelsManagementService:
    """Service for fetching, searching, and managing channel data from the database."""

    def __init__(self) -> None:
        self._sm: async_sessionmaker[AsyncSession] = DatabaseManager.get_sessionmaker()

    # ── Public API ────────────────────────────────────────────────────
    _FIRST_PAGE_SIZE: int = 50
    _PAGE_SIZE: int = 50

    async def getAllChannels(self) -> list[ChannelDataModel]:
        """Fetch all channels with their feeds and map to UI models."""
        channels = await self._fetchChannelsWithFeeds()
        return [self._mapChannel(c) for c in channels]

    async def getChannelsPage(
        self,
        offset: int = 0,
        limit: int = _PAGE_SIZE,
        filters: dict[str, Any] | None = None,
    ) -> list[ChannelDataModel]:
        """Fetch a single page of channels with optional filters."""
        channels = await self._fetchChannelsPage(offset, limit, filters)
        return [self._mapChannel(c) for c in channels]

    async def getChannelsCount(self, filters: dict[str, Any] | None = None) -> int:
        """Return total count of channels matching filters (for scrollbar)."""
        return await self._fetchChannelsCount(filters)

    async def getAllChannelsCount(self) -> int:
        """Return total count of all channels (no filters)."""
        async with self._sm() as session:
            stmt = select(func.count()).select_from(Channel)
            return (await session.execute(stmt)).scalar_one()

    async def getRecentlyAddedChannels(self, limit: int = 30) -> list[ChannelDataModel]:
        """Fetch up to ``limit`` channels added or updated within the last 30 days.

        Ordered by ``updated_at`` descending, feeds eagerly loaded.
        """
        cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        async with self._sm() as session:
            stmt = (
                select(Channel)
                .options(selectinload(Channel.feeds))
                .where(
                    Channel.updated_at >= cutoff,
                    ChannelsManagementService._hasReachableUrlsCondition(),
                )
                .order_by(Channel.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().unique().all())
        return [self._mapChannel(c) for c in channels]

    async def getChannelsByCategory(self, category: str, limit: int = 30) -> list[ChannelDataModel]:
        """Fetch up to ``limit`` channels matching a category, ordered by display name.

        Category matching is case-insensitive: "news", "News", and "NEWS" all
        resolve to the same category. Suitable for ``asyncio.gather`` to load
        several category sections in parallel.
        """
        async with self._sm() as session:
            stmt = self._buildFilteredQuery({"category": category})
            stmt = stmt.options(selectinload(Channel.feeds)).limit(limit)
            result = await session.execute(stmt)
            channels = list(result.scalars().unique().all())
        return [self._mapChannel(c) for c in channels]

    async def getTopCategoryNames(
        self,
        limit: int = 4,
        boost_names: list[str] = ["Movies", "Music"],  # noqa: B006
        min_boost_count: int = 6,
    ) -> list[str]:
        """Return the category names to surface on the home screen.

        Categories are ranked by descending channel count, ties alphabetical.

        - If there are ``limit`` or fewer distinct categories, all of them are
          returned in ranking order and no boosting is applied.
        - Otherwise, categories listed in ``boost_names`` take priority: any of
          them present in the top 8 with at least ``min_boost_count`` channels
          are promoted to the front, in the order they appear in ``boost_names``.
          The remaining slots are filled from the top 8 in ranking order.

        Matching against ``boost_names`` is case-insensitive; the returned names
        are the canonical names as stored in the database.
        """
        counts = await self._countChannelsPerCategory()

        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))

        if len(ranked) <= limit:
            return [name for name, _ in ranked]

        top8 = ranked[:8]
        boostLookup: dict[str, tuple[str, int]] = {}
        for name, count in top8:
            boostLookup[name.lower()] = (name, count)

        boosted: list[str] = []
        for candidate in boost_names:
            entry = boostLookup.get(candidate.lower())
            if entry and entry[1] >= min_boost_count:
                boosted.append(entry[0])

        remaining = [name for name, _ in top8 if name not in boosted]
        result: list[str] = boosted + remaining
        return result[:limit]

    async def _countChannelsPerCategory(self) -> dict[str, int]:
        """Count how many channels belong to each category, keyed by name."""
        async with self._sm() as session:
            stmt = select(Channel.categories).where(
                Channel.categories.isnot(None),
                ChannelsManagementService._hasReachableUrlsCondition(),
            )
            rows = (await session.execute(stmt)).scalars().all()

        counts: dict[str, int] = {}
        for cats in rows:
            if type(cats) is not list:
                continue
            for item in cats:
                if type(item) is dict:
                    name = item.get("name")
                    if name and type(name) is str:
                        counts[name] = counts.get(name, 0) + 1
        return counts

    async def getTopChannelsByVisitCount(self, limit: int = 10) -> list[ChannelDataModel]:
        """Fetch top N channels ordered by visit_count DESC, with feeds."""
        async with self._sm() as session:
            stmt = (
                select(Channel)
                .options(selectinload(Channel.feeds))
                .where(ChannelsManagementService._hasReachableUrlsCondition())
                .order_by(Channel.visit_count.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().unique().all())
        return [self._mapChannel(c) for c in channels]

    async def getM3uUrls(self, channel_id: int) -> list[str]:
        """Get all M3U URLs for a channel.

        Channel's own m3u_provided_uris come first (index 0), then feed stream URLs.

        Args:
            channel_id: Primary key of the channel.

        Returns:
            Flat list of URL strings, empty if channel not found.
        """
        async with self._sm() as session:
            stmt = select(Channel).options(selectinload(Channel.feeds)).where(Channel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()

        if not channel:
            return []

        urls: list[str] = []
        seenUrls: set[str] = set()

        if channel.m3u_provided_uris:
            for item in channel.m3u_provided_uris:
                if isinstance(item, dict) and item.get("reachable") is False:
                    continue
                url = self._extractUriFromM3uItem(item)
                if url:
                    urls.append(url)
                    seenUrls.add(url.rstrip("/"))

        for url, _langCode in self._iterFeedStreams(channel.feeds or [], seenUrls):
            urls.append(url)

        return urls

    async def getM3uStreamsWithMeta(self, channel_id: int) -> list[StreamModel]:
        """Get ordered stream model entries for a channel.

        Ordering logic mirrors getM3uUrls: channel's own m3u_provided_uris
        come first, then each feed's stream URLs.

        Each entry carries a display name (e.g. "Stream 1 (EN)") and the
        first 2-letter language code found for the source feed.
        """
        async with self._sm() as session:
            stmt = select(Channel).options(selectinload(Channel.feeds)).where(Channel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()

        if not channel:
            return []

        feeds = list(channel.feeds or [])
        channelLangCode = self._extractLangCode(feeds[0] if feeds else None)

        streams: list[StreamModel] = []
        seenUrls: set[str] = set()

        if channel.m3u_provided_uris:
            for item in channel.m3u_provided_uris:
                if isinstance(item, dict) and item.get("reachable") is False:
                    continue
                url = self._extractUriFromM3uItem(item)
                if url:
                    streams.append(self._makeStream(len(streams), url, channelLangCode))
                    seenUrls.add(url.rstrip("/"))

        for url, feedLangCode in self._iterFeedStreams(feeds, seenUrls):
            streams.append(self._makeStream(len(streams), url, feedLangCode))

        return streams

    @staticmethod
    def _extractUriFromM3uItem(item: str | dict[str, Any]) -> str:
        """Return the URL from an m3u_provided_uris entry (dict or legacy str)."""
        if isinstance(item, dict):
            return item.get("url", "")
        return item if isinstance(item, str) else ""

    @staticmethod
    def _iterFeedStreams(feeds: list[Feed], seenUrls: set[str]) -> Iterator[tuple[str, str]]:
        """Yield (url, language code) for feed streams, skipping already-seen URLs.

        Streams marked ``reachable=False`` are skipped so dead URLs are excluded.
        """
        for feed in feeds:
            feedLangCode = ChannelsManagementService._extractLangCode(feed)
            if not feed.streams:
                continue
            for stream in feed.streams:
                if isinstance(stream, dict):
                    if stream.get("reachable") is False:
                        continue
                    url = stream.get("url")
                    if url and isinstance(url, str):
                        normalized = url.rstrip("/")
                        if normalized in seenUrls:
                            continue
                        seenUrls.add(normalized)
                        yield url, feedLangCode

    @staticmethod
    def _extractLangCode(feed: Feed | None) -> str:
        """Return the 2-letter uppercase language code for a feed, or ""."""
        if not feed or not feed.languages:
            return ""
        first = feed.languages[0] if isinstance(feed.languages, list) else None
        if not first:
            return ""
        if isinstance(first, dict):
            raw = first.get("code")
        else:
            raw = first
        if not raw or not isinstance(raw, str):
            return ""
        key = raw.strip().lower()
        if len(key) == 2:
            return key.upper()
        mapped = _I639_2_TO_1.get(key, "")
        return mapped.upper()

    @staticmethod
    def _makeStream(index: int, url: str, langCode: str) -> StreamModel:
        name = f"Stream {index + 1}"
        if langCode:
            name += f" ({langCode})"
        return StreamModel(name=name, url=url, langCode=langCode)

    async def toggleFavorite(self, channel_id: int) -> bool:
        """Flip a channel's favorite flag and persist it.

        Args:
            channel_id: Primary key of the channel.

        Returns:
            The new favorite state (True if the channel is now a favorite).
        """
        async with self._sm() as session:
            channel = await session.get(Channel, channel_id)
            if not channel:
                logger.warning("Cannot toggle favorite for missing channel %s", channel_id)
                return False
            channel.is_favorite = not channel.is_favorite
            await session.commit()
            return channel.is_favorite

    async def incrementVisitCount(self, channel_id: int) -> None:
        """Increment visit_count for a channel (fire-and-forget).

        Args:
            channel_id: Primary key of the channel.
        """
        async with self._sm() as session:
            channel = await session.get(Channel, channel_id)
            if channel:
                channel.visit_count += 1
                await session.commit()
            else:
                logger.warning("Cannot increment visit_count for missing channel %s", channel_id)

    async def updateChannelReachability(
        self,
        channelId: int,
        urlToReachable: dict[str, bool],
    ) -> bool:
        """Persist probe results into a channel's ``m3u_provided_uris`` and feed streams.

        Loads the channel with its feeds, then for every item in
        ``m3u_provided_uris`` and every stream in each ``feed.streams`` whose
        URL matches a key in ``urlToReachable``, sets the item's ``reachable``
        flag. Keys in ``urlToReachable`` are normalized URLs (see
        ``normalizeUrl``); stored URLs are normalized the same way before
        matching, so entries that were never probed are left untouched.

        Args:
            channelId: Primary key of the channel.
            urlToReachable: Mapping of normalized URL -> reachable bool.

        Returns:
            True if the channel was found and updated, False otherwise.
        """
        async with self._sm() as session:
            stmt = select(Channel).options(selectinload(Channel.feeds)).where(Channel.id == channelId)
            channel = (await session.execute(stmt)).scalar_one_or_none()
            if not channel:
                logger.warning("updateChannelReachability: missing channel %s", channelId)
                return False

            if channel.m3u_provided_uris:
                channel.m3u_provided_uris = [
                    self._updateReachabilityItem(item, urlToReachable) for item in channel.m3u_provided_uris
                ]

            for feed in channel.feeds or []:
                if not feed.streams:
                    continue
                feed.streams = [self._updateReachabilityItem(stream, urlToReachable) for stream in feed.streams]

            await session.commit()
            return True

    @staticmethod
    def _updateReachabilityItem(
        item: Any,
        urlToReachable: dict[str, bool],
    ) -> Any:
        """Return ``item`` with ``reachable`` synced to ``urlToReachable``.

        Non-dict items and URLs without a probe result are returned untouched.
        """
        if not isinstance(item, dict):
            return item
        url = item.get("url")
        if not url or not isinstance(url, str):
            return item
        key = normalizeUrl(url)
        if key in urlToReachable:
            updated = dict(item)
            updated["reachable"] = urlToReachable[key]
            return updated
        return item

    async def getDistinctCategories(self) -> list[str]:
        """Fetch unique category names across displayable channels, sorted A-Z."""
        async with self._sm() as session:
            stmt = select(Channel.categories).where(
                Channel.categories.isnot(None),
                ChannelsManagementService._hasReachableUrlsCondition(),
            )
            rows = (await session.execute(stmt)).scalars().all()
        seen: set[str] = set()
        for cats in rows:
            if type(cats) is list:
                for item in cats:
                    if type(item) is dict:
                        name = item.get("name")
                        if name and type(name) is str:
                            seen.add(name)
        return sorted(seen)

    async def hasUncategorizedChannels(self) -> bool:
        """Return True if any displayable channel has no categories (NULL or empty list)."""
        async with self._sm() as session:
            stmt = (
                select(Channel.id)
                .where(
                    Channel.categories.is_(None) | (func.json_array_length(Channel.categories) == 0),
                    ChannelsManagementService._hasReachableUrlsCondition(),
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.first() is not None

    async def getDistinctCountries(self) -> list[tuple[str, str]]:
        """Fetch distinct country (code, name) pairs from displayable channels, sorted by name."""
        async with self._sm() as session:
            codeCol = func.json_extract(Channel.country, "$.code")
            nameCol = func.json_extract(Channel.country, "$.name")
            stmt = (
                select(codeCol, nameCol)
                .where(
                    Channel.country.isnot(None),
                    ChannelsManagementService._hasReachableUrlsCondition(),
                )
                .distinct()
            )
            rows = (await session.execute(stmt)).all()
        seen: dict[str, str] = {}
        for code, name in rows:
            if code and type(code) is str:
                seen[code] = name if name and type(name) is str else code
        items = [(code, name) for code, name in seen.items()]
        items.sort(key=lambda x: x[1].lower())
        return items

    # ── DB fetch ──────────────────────────────────────────────────────

    async def _fetchChannelsWithFeeds(self) -> list[Channel]:
        """Query channels with eager-loaded feeds, ordered by display name."""
        async with self._sm() as session:
            stmt = (
                select(Channel)
                .options(selectinload(Channel.feeds))
                .where(ChannelsManagementService._hasReachableUrlsCondition())
                .order_by(Channel.display_name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().unique().all())

    async def _fetchChannelsPage(
        self,
        offset: int,
        limit: int,
        filters: dict[str, Any] | None,
    ) -> list[Channel]:
        """Fetch a page of channels with filters applied."""
        async with self._sm() as session:
            stmt = self._buildFilteredQuery(filters)
            stmt = stmt.options(selectinload(Channel.feeds)).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().unique().all())

    async def _fetchChannelsCount(self, filters: dict[str, Any] | None) -> int:
        """Count total channels matching filters."""
        async with self._sm() as session:
            stmt = self._buildFilteredQuery(filters)
            stmt = select(func.count()).select_from(stmt.subquery())
            result = await session.execute(stmt)
            return result.scalar_one()

    def _buildFilteredQuery(self, filters: dict[str, Any] | None) -> Select[tuple[Channel]]:
        """Build base query with optional WHERE clauses."""
        stmt = select(Channel).order_by(Channel.display_name)
        stmt = stmt.where(ChannelsManagementService._hasReachableUrlsCondition())
        if not filters:
            return stmt

        conditions = []
        if filters.get("category"):
            conditions.append(self._categoryCondition(filters["category"]))
        if filters.get("favorite"):
            conditions.append(Channel.is_favorite.is_(True))
        if filters.get("quality"):
            stmt = stmt.join(Channel.feeds)
            qualityFormats = _QUALITY_TO_FORMATS.get(filters["quality"], [])
            if qualityFormats:
                conditions.append(Feed.format.in_(qualityFormats))
        if filters.get("country"):
            conditions.append(func.upper(func.json_extract(Channel.country, "$.code")) == filters["country"].upper())
        if filters.get("search"):
            searchTerm = f"%{filters['search'].lower()}%"
            conditions.append(
                Channel.display_name.ilike(searchTerm)
                | Channel.channel_id.ilike(searchTerm)
                | Channel.canonical_name.ilike(searchTerm)
            )
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    @classmethod
    def _hasReachableUrlsCondition(cls) -> Any:
        """Build a WHERE condition for channels that have at least one reachable URL.

        A channel qualifies if any URL in its ``m3u_provided_uris`` or any stream
        in any of its feeds has ``reachable: true`` (JSON boolean). Entries marked
        ``false`` or never probed (no ``reachable`` key) do not count.

        Uses SQLite JSON1 ``json_each`` + ``json_extract``: JSON ``true`` extracts
        as the integer ``1``, so ``= 1`` matches only ``true`` (verified against
        sqlite3 3.45).
        """
        m3uJsonEach = func.json_each(Channel.m3u_provided_uris).table_valued("value")
        m3uReachable = exists(
            select(1).select_from(m3uJsonEach).where(func.json_extract(m3uJsonEach.c.value, "$.reachable") == 1)
        )

        feedJsonEach = func.json_each(Feed.streams).table_valued("value")
        feedReachable = exists(
            select(1)
            .select_from(Feed.__table__.join(feedJsonEach, true()))
            .where(
                Feed.__table__.c.channel_id == Channel.id,
                func.json_extract(feedJsonEach.c.value, "$.reachable") == 1,
            )
        )

        return or_(m3uReachable, feedReachable)

    @staticmethod
    def _categoryCondition(categoryValue: str) -> Any:
        """Build the WHERE condition for a category filter value."""
        cats = [c.strip().lower() for c in categoryValue.split(",") if c.strip()]
        if "uncategorized" in cats:
            return Channel.categories.is_(None) | (func.json_array_length(Channel.categories) == 0)
        json_each_tv = func.json_each(Channel.categories).table_valued("value")
        catSubq = (
            select(1)
            .select_from(json_each_tv)
            .where(func.lower(func.json_extract(json_each_tv.c.value, "$.name")).in_(cats))
        )
        return exists(catSubq)

    # ── Top-level mapper ──────────────────────────────────────────────

    @staticmethod
    def _iterReachableM3uUrls(channel: Channel) -> Iterator[str]:
        """Yield reachable URLs from a channel's m3u_provided_uris items."""
        for item in channel.m3u_provided_uris or []:
            if isinstance(item, dict) and item.get("reachable") is False:
                continue
            url = ChannelsManagementService._extractUriFromM3uItem(item)
            if url:
                yield url

    @staticmethod
    def _iterReachableFeedUrls(feeds: list[Feed]) -> Iterator[str]:
        """Yield reachable stream URLs across the given feeds."""
        for feed in feeds:
            for stream in feed.streams or []:
                if not isinstance(stream, dict) or stream.get("reachable") is False:
                    continue
                url = stream.get("url")
                if url and isinstance(url, str):
                    yield url

    @staticmethod
    def _countUniqueStreamUrls(channel: Channel, feeds: list[Feed]) -> int:
        """Count unique stream URLs across m3u_provided_uris and feed streams."""
        seenUrls: set[str] = set()
        for url in ChannelsManagementService._iterReachableM3uUrls(channel):
            seenUrls.add(url.rstrip("/"))
        for url in ChannelsManagementService._iterReachableFeedUrls(feeds):
            seenUrls.add(url.rstrip("/"))
        return len(seenUrls)

    def mapChannel(self, channel: Channel) -> ChannelDataModel:
        """Map a Channel ORM instance to a ChannelDataModel (public API)."""
        return self._mapChannel(channel)

    def _mapChannel(self, channel: Channel) -> ChannelDataModel:
        """Map a Channel ORM instance to a ChannelDataModel."""
        feeds: list[Feed] = list(channel.feeds) if channel.feeds else []
        quality, resolution = self._determineQualityAndResolution(feeds, channel)
        return ChannelDataModel(
            channelId=channel.id,
            displayName=self._getDisplayName(channel),
            logoUrl=self._resolveFirstWorkingLogo(channel.tvg_logos),
            countryCode=self._extractCountryCode(channel),
            category=self._extractCategory(channel),
            quality=quality,
            resolution=resolution,
            feedCount=self._countUniqueStreamUrls(channel, feeds),
            visitCount=channel.visit_count,
            isFavorite=bool(channel.is_favorite),
            # TODO: implement live stream detection logic
            isLive=True,
            websiteUrl=channel.website or "",
            languages=self._aggregateLanguages(feeds),
            altNames=self._extractAltNames(channel),
            additionalTags=self._extractFlags(channel),
        )

    # ── Display name ──────────────────────────────────────────────────

    def _getDisplayName(self, channel: Channel) -> str:
        """Return the best available display name for a channel."""
        return channel.display_name or channel.canonical_name or channel.channel_id

    # ── Country ───────────────────────────────────────────────────────

    def _extractCountryCode(self, channel: Channel) -> str:
        """Extract the uppercase ISO country code from the country JSON."""
        if not channel.country:
            return ""
        code: object = channel.country.get("code", "")
        return str(code).upper() if code else ""

    # ── Category ──────────────────────────────────────────────────────

    def _extractCategory(self, channel: Channel) -> str:
        """Extract category names from structured category data."""
        seen: set[str] = set()
        if channel.categories and type(channel.categories) is list:
            for item in channel.categories:
                if type(item) is dict:
                    name = item.get("name")
                    if name and type(name) is str:
                        seen.add(name)
        return ", ".join(sorted(seen)) if seen else "Uncategorized"

    # ── Alt names ─────────────────────────────────────────────────────

    def _extractAltNames(self, channel: Channel) -> str:
        """Join alt_names JSON list into a comma-separated string."""
        if not channel.alt_names or type(channel.alt_names) is not list:
            return ""
        return ", ".join(name for name in channel.alt_names if type(name) is str and name)

    # ── Flags → additional tags ───────────────────────────────────────

    def _extractFlags(self, channel: Channel) -> str:
        """Join flags JSON list into a comma-separated, title-cased string."""
        if not channel.flags or type(channel.flags) is not list:
            return ""
        parts: list[str] = []
        for flag in channel.flags:
            if flag:
                parts.append(str(flag).replace("-", " ").title())
        return ", ".join(parts)

    # ── Languages ─────────────────────────────────────────────────────

    def _aggregateLanguages(self, feeds: list[Feed]) -> str:
        """Collect unique language names from all feeds, comma-separated."""
        seen: set[str] = set()
        for feed in feeds:
            if feed.languages and type(feed.languages) is list:
                for lang in feed.languages:
                    if not lang:
                        continue
                    if type(lang) is str:
                        seen.add(lang)
                    elif type(lang) is dict:
                        name = lang.get("name") or lang.get("code") or str(lang)
                        seen.add(name)
        return ", ".join(sorted(seen))

    # ── Logo ──────────────────────────────────────────────────────────

    def _resolveFirstWorkingLogo(self, logos: list[str] | None) -> str:
        """Return the first logo URL; async HEAD checks will replace this later.

        TODO: Replace with async httpx HEAD requests to verify each URL:
              async with httpx.AsyncClient(timeout=5) as client:
                  for url in logos:
                      try:
                          resp = await client.head(url)
                          if resp.status_code == 200:
                              return url
                      except httpx.RequestError:
                          continue
        """
        if not logos or type(logos) is not list:
            return ""
        return logos[0] if logos else ""

    # ── Quality & resolution ──────────────────────────────────────────

    def _parseResolution(self, raw: str) -> tuple[int, int, str] | None:
        """Parse a resolution string into (numeric, scanScore, fullRes).

        "1080p" → (1080, 1, "1080p")
        "1080i" → (1080, 0, "1080i")
        "720"   → (720, 1, "720p")
        """
        m = re.fullmatch(r"(\d+)\s*(p|i)?", raw.strip())
        if not m:
            return None
        numeric = int(m.group(1))
        scan = m.group(2) or "p"
        score = 1 if scan == "p" else 0
        return (numeric, score, f"{numeric}{scan}")

    def _numericToQuality(self, num: int) -> str:
        """Map a numeric resolution to its standard quality label."""
        return _RESOLUTION_TO_QUALITY.get(num, "")

    def _collectFeedResolutions(self, feeds: list[Feed], candidates: list[tuple[int, int, str]]) -> None:
        """Collect resolution candidates from each feed's format column."""
        for feed in feeds:
            if not feed.format:
                continue
            parsed = self._parseResolution(feed.format)
            if parsed:
                candidates.append(parsed)
            else:
                mapped = _FORMAT_TO_RESOLUTION.get(feed.format)
                if mapped:
                    parsed = self._parseResolution(mapped)
                    if parsed:
                        candidates.append(parsed)

    def _determineQualityAndResolution(
        self,
        feeds: list[Feed],
        channel: Channel,
    ) -> tuple[str, str]:
        """Determine quality label and resolution string from all available sources.

        Sources (in order of collection, best wins):
        1. channel.resolutions — always checked
        2. feeds[*].format — only if channel has feeds

        Falls back to ("SD", "") when nothing is found.
        """
        candidates: list[tuple[int, int, str]] = []

        if channel.resolutions and type(channel.resolutions) is list:
            for res in channel.resolutions:
                parsed = self._parseResolution(res)
                if parsed:
                    candidates.append(parsed)

        if feeds:
            self._collectFeedResolutions(feeds, candidates)

        if candidates:
            candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            bestNum, _, bestRes = candidates[0]
            quality = self._numericToQuality(bestNum)
            return quality, bestRes

        return "SD", ""
