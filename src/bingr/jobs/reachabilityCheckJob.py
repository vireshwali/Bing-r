"""Periodic reachability probe for channel M3U URLs and feed stream URLs.

The job loads stored URLs (``Channel.m3u_provided_uris`` items and
``Feed.streams`` items) in batches of ``CHANNEL_BATCH_SIZE`` and probes each one
over HTTP(S) via :class:`~bingr.services.httpProbeService.HttpProbeService`,
which wraps Qt's ``QNetworkAccessManager`` — the only HTTP stack that works
under QtAsyncio, which does not implement the Level 2 asyncio networking API.
URLs that pass the HTTP probe are then re-validated with
:class:`~bingr.services.ffprobeService.FfprobeService` (a ``QProcess``
subprocess per URL, capped by the service's concurrency) so a
served-but-broken stream is downgraded to unreachable. A final ``reachable``
boolean is written back into each JSON item, via
``ChannelsManagementService.updateChannelReachability``, so the UI can decide
whether a channel has live streams.

Channels are processed in small batches — load, probe, persist, release — so
memory never grows with the whole playlist and results reach the DB
incrementally instead of in one shot at the end.

All per-batch state is kept local to the batch and released once results are
persisted: ``results``, ``urlToChannelIds`` and ``keyToUrl`` never outlive a
single batch. The signal-handler state that makes HTTP probing work lives
inside the probe service instance and is reset by it at the start of every
batch.

Duplicates are removed before any request is fired: the same URL can appear in
both ``m3u_provided_uris`` and ``feed.streams`` for one channel, and across
channels. Comparison is case-sensitive (``QUrl`` normalises scheme and host but
preserves path case, matching HTTP semantics); dedup keys come from
``commonUtils.normalizeUrl``.

The job runs periodically (every ``CHECK_INTERVAL_MINUTES``) over all channels,
and on demand via ``appEventBus.reachabilityCheckRequested`` with a specific
list of channel IDs. An on-demand request that arrives while a run is active is
queued and drained as a targeted pass once the current run finishes. Runs are
guard-railed against overlap.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from collections.abc import AsyncIterator, Sequence

from PySide6.QtCore import QObject, QTimer, Slot
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bingr.common.commonUtils import normalizeUrl, trimHeap
from bingr.common.eventBus import appEventBus
from bingr.db.dbManager import DatabaseManager
from bingr.db.models import Channel
from bingr.services.channelsManagementService import ChannelsManagementService
from bingr.services.ffprobeService import FfprobeService
from bingr.services.httpProbeService import HttpProbeService

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 60
CHANNEL_BATCH_SIZE = 20


class ReachabilityCheckJob(QObject):
    """Periodically probes channel URLs and writes reachability back to the DB."""

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._running = False
        self._stopped = False
        self._queuedChannelIds: list[int] = []

        # Services own their own network manager / subprocess handling and
        # their own defaults; the job only orchestrates them.
        self._httpProbe = HttpProbeService()
        self._ffprobe = FfprobeService()
        self._channelService = ChannelsManagementService()

        appEventBus.reachabilityCheckRequested.connect(self._onRequested)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._onTimer)
        self._timer.start(CHECK_INTERVAL_MINUTES * 60 * 1000)
        logger.info(
            "ReachabilityCheckJob scheduled to run every %s minute(s)",
            CHECK_INTERVAL_MINUTES,
        )

    # ------------------------------------------------------------------
    # Entry points: periodic timer (all channels) and event bus (specific IDs)
    # ------------------------------------------------------------------

    @Slot(object)
    def _onRequested(self, channelIds: Sequence[int] | None = None) -> None:
        ids = [int(cid) for cid in channelIds] if channelIds else []
        if self._running:
            if ids:
                self._queuedChannelIds.extend(ids)
                logger.info(
                    "ReachabilityCheckJob queued %d channel ID(s) for after the current run",
                    len(ids),
                )
            return
        if not ids:
            logger.info("ReachabilityCheckJob: on-demand request with no channel IDs — skipping")
            return
        logger.info("ReachabilityCheckJob triggered via event bus for %d channel ID(s)", len(ids))
        self._onTimer(ids)

    def _onTimer(self, channelIds: Sequence[int] | None = None) -> None:
        if self._running:
            logger.info("ReachabilityCheckJob skipped (previous run still active)")
            return

        asyncio.create_task(self._run(channelIds))  # noqa: RUF006

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def _run(self, channelIds: Sequence[int] | None = None) -> None:
        self._running = True
        logger.info("ReachabilityCheckJob started.")

        # Lower the gen0 GC threshold during the probe phase so ORM/network
        # cycles and per-batch dicts are collected ~3x faster; restore the
        # defaults in the finally block.
        origThresholds = gc.get_threshold()
        gc.set_threshold(200, origThresholds[1], origThresholds[2])

        totalProbed = 0
        totalBatches = 0
        probeStartedAt = time.monotonic()

        try:
            sm = DatabaseManager.get_sessionmaker()

            # First pass: timer sweep (None) or the specific IDs that triggered
            # us, merged with anything queued while we were starting up.
            targetIds: set[int] | None = None
            if channelIds:
                targetIds = set(channelIds)
            if self._queuedChannelIds:
                if targetIds is None:
                    targetIds = set()
                targetIds.update(self._queuedChannelIds)
                self._queuedChannelIds.clear()

            while True:
                if targetIds is None:
                    iterator = self._channelBatches(sm, CHANNEL_BATCH_SIZE)
                else:
                    iterator = self._channelsByIds(sm, targetIds, CHANNEL_BATCH_SIZE)

                probed, batches = await self._probeAll(iterator)
                totalProbed += probed
                totalBatches += batches

                # Drain any on-demand IDs that arrived while we were running.
                if not self._queuedChannelIds:
                    break
                targetIds = set(self._queuedChannelIds)
                self._queuedChannelIds.clear()

            if totalBatches == 0 or totalProbed == 0:
                logger.info("[Reachability] Check finished: no URLs to probe")
            else:
                elapsed = time.monotonic() - probeStartedAt
                logger.info(
                    "Reachability Check complete: %d URL(s) in %d batch(es), done in %.1fs",
                    totalProbed,
                    totalBatches,
                    elapsed,
                )
        except Exception:
            logger.exception("Reachability check failed")
        finally:
            self._running = False
            gc.set_threshold(origThresholds[0], origThresholds[1], origThresholds[2])
            gc.collect()
            trimHeap()
            if not self._stopped:
                self._timer.start(CHECK_INTERVAL_MINUTES * 60 * 1000)

    async def _probeAll(
        self,
        iterator: AsyncIterator[list[Channel]],
    ) -> tuple[int, int]:
        """Iterate channel batches, probe each and persist the results.

        Returns ``(totalProbed, totalBatches)`` so the caller can log a summary.
        Every batch is released — ``del`` + ``gc.collect()`` + ``trimHeap()`` —
        right after its results are written to the DB.
        """
        totalProbed = 0
        totalBatches = 0
        async for batchChannels in iterator:
            totalBatches += 1

            batchChannelIds = {channel.id for channel in batchChannels}

            results, urlToChannelIds = await self._processBatch(batchChannels)
            totalProbed += len(results)

            await self._persistBatch(batchChannelIds, results, urlToChannelIds)

            del batchChannels
            gc.collect()
            trimHeap()
        return totalProbed, totalBatches

    # ------------------------------------------------------------------
    # Batch loading
    # ------------------------------------------------------------------

    async def _channelBatches(
        self,
        sm: object,
        batchSize: int,
    ) -> AsyncIterator[list[Channel]]:
        """Yield all channels in chunks of ``batchSize``, releasing between chunks.

        Each chunk is fetched in a fresh session that calls ``expunge_all``
        and closes before the next chunk, so the SQLAlchemy identity map never
        grows beyond one batch.
        """
        offset = 0
        while True:
            async with sm() as session:
                stmt = (
                    select(Channel)
                    .options(selectinload(Channel.feeds))
                    .order_by(Channel.id)
                    .limit(batchSize)
                    .offset(offset)
                )
                batch = list((await session.execute(stmt)).scalars().unique().all())
                session.expunge_all()
            if not batch:
                return

            yield batch
            gc.collect()
            trimHeap()

            offset += batchSize

    async def _channelsByIds(
        self,
        sm: object,
        channelIds: set[int],
        batchSize: int,
    ) -> AsyncIterator[list[Channel]]:
        """Yield only the given channel IDs in chunks, for on-demand runs.

        Avoids an offset sweep over the whole table when a handful of freshly
        imported channels need probing.
        """
        ids = sorted(channelIds)
        for start in range(0, len(ids), batchSize):
            chunk = ids[start : start + batchSize]
            async with sm() as session:
                stmt = (
                    select(Channel)
                    .options(selectinload(Channel.feeds))
                    .where(Channel.id.in_(chunk))
                    .order_by(Channel.id)
                )
                batch = list((await session.execute(stmt)).scalars().unique().all())
                session.expunge_all()
            if not batch:
                continue

            yield batch
            gc.collect()
            trimHeap()

    # ------------------------------------------------------------------
    # Per-batch probing: local state, released after persist
    # ------------------------------------------------------------------

    async def _processBatch(
        self,
        batchChannels: list[Channel],
    ) -> tuple[dict[str, bool], dict[str, set[int]]]:
        """Enqueue, probe and collect results for one channel batch.

        All dedup/result state that the persist step needs is built and returned
        here; nothing outlives the batch. HTTP probing and ffprobe validation
        are delegated to the probe services; each resets its own signal-handler
        state at the start of the call.
        """
        urlToChannelIds: dict[str, set[int]] = {}
        keyToUrl: dict[str, str] = {}

        for channel in batchChannels:
            self._enqueueChannel(channel, urlToChannelIds, keyToUrl)

        if not keyToUrl:
            return {}, urlToChannelIds

        logger.info(
            "Starting probe batch of %d channel(s) -> %d unique URL(s)",
            len(batchChannels),
            len(keyToUrl),
        )

        results = await self._httpProbe.probeBatch(keyToUrl)
        await self._ffprobe.validateBatch(results, keyToUrl)
        return results, urlToChannelIds

    def _enqueueChannel(
        self,
        channel: Channel,
        urlToChannelIds: dict[str, set[int]],
        keyToUrl: dict[str, str],
    ) -> None:
        """Collect a channel's URLs into the batch's dedup maps."""
        for item in channel.m3u_provided_uris or []:
            if isinstance(item, dict):
                url = item.get("url")
                if url and isinstance(url, str):
                    self._enqueueUrl(url, channel.id, urlToChannelIds, keyToUrl)
        for feed in channel.feeds or []:
            for stream in feed.streams or []:
                if isinstance(stream, dict):
                    url = stream.get("url")
                    if url and isinstance(url, str):
                        self._enqueueUrl(url, channel.id, urlToChannelIds, keyToUrl)

    def _enqueueUrl(
        self,
        url: str,
        channelId: int,
        urlToChannelIds: dict[str, set[int]],
        keyToUrl: dict[str, str],
    ) -> None:
        """Register ``url`` once per dedup key, mapping it to its channels."""
        key = normalizeUrl(url)
        keyToUrl[key] = url
        urlToChannelIds.setdefault(key, set()).add(channelId)

    # ------------------------------------------------------------------
    # Persist results to DB
    # ------------------------------------------------------------------

    async def _persistBatch(
        self,
        batchChannelIds: set[int],
        results: dict[str, bool],
        urlToChannelIds: dict[str, set[int]],
    ) -> None:
        """Persist the current batch's results via ChannelsManagementService."""
        try:
            byChannel: dict[int, dict[str, bool]] = {}
            for key, reachable in results.items():
                for channelId in urlToChannelIds.get(key, ()):
                    if channelId in batchChannelIds:
                        byChannel.setdefault(channelId, {})[key] = reachable

            if not byChannel:
                return

            logger.info("Saving reachability results for %d channel(s)", len(byChannel))
            for channelId, urlToReachable in byChannel.items():
                await self._channelService.updateChannelReachability(channelId, urlToReachable)
        except Exception:
            logger.exception("Reachability check persist failed")

    def stop(self) -> None:
        """Gracefully stop the periodic timer."""
        self._stopped = True
        self._timer.stop()
        logger.info("ReachabilityCheckJob stopped")
