"""M3U playlist import pipeline — the main entry point for importing playlists.

importM3u() copies/downloads a playlist to the workspace, creates a M3USource
record, enriches every segment via enrichmentHelper, and upserts channels,
feeds, and M3U links into the DB. importM3uToDb() handles the per-segment
loop with dedup/merge logic.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import m3u8  # pyright: ignore[reportMissingModuleSource]
import orjson  # pyright: ignore[reportMissingModuleSource]
from sqlalchemy import select

from bingr.common.config import getConfig
from bingr.common.constants import KEYS
from bingr.common.exceptions import (
    DownloadError,
    MissingSourceParamsError,
    ProcessingError,
    SourceAlreadyImportedError,
)
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel, Feed, M3UChannel, M3USource, utcnow
from bingr.services.helpers.enrichmentHelper import (
    enrichSegment,
    ensureAllCaches,
    isCountryName,
    resolveChannelId,
)
from bingr.services.helpers.parsingHelper import parseIptvAttributesEnhanced, parseTvgId

logger = logging.getLogger(__name__)


def _mergeUniqueStr(existing: list[str] | None, newItems: list[str], *, caseSensitive: bool = True) -> list[str]:
    current = list(existing) if existing else []
    if caseSensitive:
        existingSet = set(current)
        for item in newItems:
            if item and str(item) not in existingSet:
                current.append(item)
                existingSet.add(str(item))
    else:
        existingLower = {s.lower() for s in current if s}
        for item in newItems:
            if item and str(item).lower() not in existingLower:
                current.append(item)
                existingLower.add(str(item).lower())
    return current


def _mergeCategories(existing: list[dict[str, Any]] | None, newCats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = list(existing) if existing else []
    seenIds = {c.get("id") for c in current if c.get("id")}
    for cat in newCats:
        if cat.get("id") and cat["id"] not in seenIds:
            current.append(cat)
            seenIds.add(cat["id"])
    return current


async def _findChannel(session, channel_id: str) -> Channel | None:
    if not channel_id:
        return None
    stmt = select(Channel).where(Channel.channel_id == channel_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _insertChannel(session, channel_id: str, sourceId: int, enriched: dict[str, Any]) -> Channel:
    chData = enriched.get("channel") or {}
    _, prefix, suffix = parseTvgId(enriched.get("tvg_id", ""))

    uri = enriched.get("uri", "")
    tvg_id = enriched.get("tvg_id", "")
    title = enriched.get("title", "")
    clean_title = enriched.get("clean_title", "")
    tvg_name = enriched.get("tvg_name", "")
    group_title = enriched.get("group_title", "")
    group_title = group_title if not isCountryName(group_title) else ""
    tvg_logo = enriched.get("tvg_logo", "")
    resolution = enriched.get("resolution", "")
    channel = Channel(
        channel_id=channel_id,
        tvg_prefix=prefix,
        tvg_suffix=suffix,
        tvg_ids=[tvg_id] if tvg_id else [],
        titles=[title] if title else [],
        clean_titles=[clean_title] if clean_title else [],
        display_name=enriched.get("display_name", ""),
        tvg_names=[tvg_name] if tvg_name else [],
        group_titles=[group_title] if group_title else [],
        tvg_logos=[tvg_logo] if tvg_logo else [],
        resolutions=[resolution] if resolution else [],
        flags=enriched.get("flags", []),
        m3u_provided_uris=[uri] if uri else [],
        matched_feed_id=enriched.get("matched_feed_id", ""),
        canonical_name=(chData or {}).get("name", enriched.get("clean_title", "")),
        alt_names=(chData or {}).get("alt_names", []),
        categories=[c for c in ((chData or {}).get("categories", [])) if not isCountryName(c.get("name", ""))],
        country=enriched.get("country"),
        website=(chData or {}).get("website"),
    )
    session.add(channel)
    await session.flush()
    logger.info("db: inserted channel channel_id=%r (source_id=%d)", channel_id, sourceId)
    return channel


async def _upsertFeeds(session, channelPk: int, enriched: dict[str, Any]):
    feeds = enriched.get("feeds") or []
    for f in feeds:
        feed_id = f.get("id", "")
        if not feed_id:
            continue

        stmt = select(Feed).where(Feed.channel_id == channelPk, Feed.feed_id == feed_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.format = f.get("format", existing.format)
            existing.feed_name = f.get("name", existing.feed_name)
            existing.is_main = f.get("is_main", existing.is_main)
            existing.broadcast_area = f.get("broadcast_area", existing.broadcast_area)
            existing.languages = f.get("languages", existing.languages)
            existing.streams = f.get("streams", existing.streams)
            existing.updated_at = utcnow()
        else:
            feed = Feed(
                channel_id=channelPk,
                feed_id=feed_id,
                feed_name=f.get("name", ""),
                format=f.get("format", ""),
                is_main=f.get("is_main", False),
                broadcast_area=f.get("broadcast_area", []),
                languages=f.get("languages", []),
                streams=f.get("streams", []),
            )
            session.add(feed)


async def _linkM3uChannel(session, channelPk: int, sourceId: int):
    stmt = select(M3UChannel).where(
        M3UChannel.channel_id == channelPk,
        M3UChannel.source_id == sourceId,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if not existing:
        session.add(M3UChannel(channel_id=channelPk, source_id=sourceId))


async def importM3uToDb(m3uPath: Path, sourceId: int, session, sourceName: str = "") -> int:
    logger.info("Importing %s to DB (source_id=%d, source=%r) ...", m3uPath.name, sourceId, sourceName)

    playlist = m3u8.load(str(m3uPath), custom_tags_parser=parseIptvAttributesEnhanced)

    epgUrls = playlist.data.get("x_tvg_url", []) if hasattr(playlist, "data") else []
    if epgUrls:
        logger.info("  x-tvg-url: %d EPG URLs from header", len(epgUrls))
        src = (await session.execute(select(M3USource).where(M3USource.id == sourceId))).scalar_one()
        src.m3u_provided_epg_url = orjson.dumps(epgUrls).decode()

    total = len(playlist.segments)

    count = 0
    errors = 0
    for i, seg in enumerate(playlist.segments, 1):
        try:
            enriched = enrichSegment(seg)
        except Exception as e:
            logger.error("Failed to enrich segment %d: %s", i, e)
            errors += 1
            continue

        chId = resolveChannelId(sourceName or f"src_{sourceId}", enriched)
        uri = enriched.get("uri", "")
        tvg_id = enriched.get("tvg_id", "")

        if not uri:
            logger.warning("import: segment %d has no URI, skipping", i)
            continue

        existing = await _findChannel(session, chId)
        if existing:
            uris = existing.m3u_provided_uris or []
            is_dup_uri = uri in uris

            if not is_dup_uri:
                existing.m3u_provided_uris = _mergeUniqueStr(uris, [uri], caseSensitive=True)

            existing.tvg_ids = _mergeUniqueStr(existing.tvg_ids, [tvg_id], caseSensitive=True)
            existing.titles = _mergeUniqueStr(existing.titles, [enriched.get("title", "")], caseSensitive=False)
            existing.clean_titles = _mergeUniqueStr(
                existing.clean_titles, [enriched.get("clean_title", "")], caseSensitive=False
            )
            existing.tvg_names = _mergeUniqueStr(
                existing.tvg_names, [enriched.get("tvg_name", "")], caseSensitive=False
            )
            newGroup = enriched.get("group_title", "")
            newGroup = newGroup if not isCountryName(newGroup) else ""
            existing.group_titles = _mergeUniqueStr(existing.group_titles, [newGroup], caseSensitive=False)
            existing.tvg_logos = _mergeUniqueStr(existing.tvg_logos, [enriched.get("tvg_logo", "")], caseSensitive=True)
            existing.resolutions = _mergeUniqueStr(
                existing.resolutions, [enriched.get("resolution", "")], caseSensitive=False
            )
            existing.flags = _mergeUniqueStr(existing.flags, enriched.get("flags", []), caseSensitive=False)
            newCats = (enriched.get("channel") or {}).get("categories", [])
            existing.categories = _mergeCategories(
                existing.categories,
                [c for c in newCats if not isCountryName(c.get("name", ""))],
            )
            existing.updated_at = utcnow()
            await _upsertFeeds(session, existing.id, enriched)
            await _linkM3uChannel(session, existing.id, sourceId)
            logger.debug("import: accumulated segment %d (%s @ %s)", i, chId, uri[:60])
        else:
            channel = await _insertChannel(session, chId, sourceId, enriched)
            await _upsertFeeds(session, channel.id, enriched)
            await _linkM3uChannel(session, channel.id, sourceId)
            count += 1

        if count % 50 == 0:
            logger.info("  progress: %d/%d channels imported", count, total)

    await session.flush()
    logger.info(
        "Imported %d channels from %s (%d segments, %d errors)",
        count,
        m3uPath.name,
        total,
        errors,
    )
    return count


async def importM3u(
    sourceName: str,
    m3uPath: Path | None = None,
    url: str | None = None,
    config=None,
) -> M3USource:
    cfg = config or getConfig()
    playlists_dir = cfg.workspacePath() / "playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)
    ensureAllCaches()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # TODO: Remove it later. simulate a delay to mimic real-world scenarios where the import might take some time
        # await asyncio.sleep(10)

        if m3uPath is not None:
            m3uPath = m3uPath.resolve()
            inputKey = str(m3uPath)
            suffix = m3uPath.suffix if m3uPath.suffix else ".m3u"
            if m3uPath.parent.resolve() == playlists_dir.resolve():
                dst = m3uPath
                logger.info("Using existing file %s (already in playlists dir)", dst)
            else:
                dst = playlists_dir / f"{m3uPath.stem}_{timestamp}{suffix}"
                dst.write_bytes(m3uPath.read_bytes())
                logger.info("Copied %s -> %s", m3uPath, dst)
            colLabel = "input_file"
        elif url is not None:
            inputKey = url
            parsedUrl = urlparse(url)
            urlPath = parsedUrl.path
            urlName = urlPath.rsplit("/", 1)[-1] if urlPath else "playlist"
            stem, suffix = Path(urlName).stem, Path(urlName).suffix
            suffix = suffix if suffix else ".m3u"
            dst = playlists_dir / f"{stem}_{timestamp}{suffix}"
            logger.info("Downloading %s -> %s", url, dst)
            try:
                timeout = cfg.getInt(KEYS.DOWNLOAD_TIMEOUT, 120)
                content = await asyncio.to_thread(
                    lambda: httpx.Client().get(url, timeout=timeout).content,
                )
            except Exception as e:
                raise DownloadError(
                    f"Failed to download playlist from {url}: {e}",
                    details={"url": url},
                ) from e
            dst.write_bytes(content)
            colLabel = "input_url"
        else:
            raise MissingSourceParamsError()

        sessionMaker = DatabaseManager.get_sessionmaker()
        async with sessionMaker(expire_on_commit=False) as session:
            # TODO: Content-hash re-ingestion — use SHA-256 to detect content
            # changes. If same inputKey but content differs, allow re-import
            # with channel merge instead of raising SourceAlreadyImportedError.
            stmt = select(M3USource).where(
                M3USource.input_file == inputKey if m3uPath else M3USource.input_url == inputKey
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                raise SourceAlreadyImportedError(existing.id, existing.name, colLabel, inputKey)

            source = M3USource(
                name=sourceName,
                input_url=url,
                input_file=str(m3uPath) if m3uPath else None,
                path=str(dst),
                channel_count=0,
            )
            session.add(source)
            await session.flush()

            channel_count = await importM3uToDb(dst, source.id, session, sourceName)

            source.channel_count = channel_count
            await session.commit()
            logger.info("Source %r: imported %d channels", sourceName, channel_count)
            return source
    except ProcessingError:
        raise
    except Exception as e:
        raise ProcessingError(
            str(e),
            reason="unexpected_error",
            details={"traceback": traceback.format_exc()},
        ) from e
