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
import math
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

CHECK_INTERVAL_MINUTES = 5
CHANNEL_BATCH_SIZE = 20


class ReachabilityCheckJob(QObject):
    """Periodically probes channel URLs and writes reachability back to the DB."""

    def __init__(
        self,
        parent: QObject | None = None,
        ffprobePath: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._running = False
        self._stopped = False
        self._queuedChannelIds: list[int] = []

        # Services own their own network manager / subprocess handling and
        # their own defaults; the job only orchestrates them. ffprobePath lets
        # callers point at a local ffprobe binary for development.
        self._httpProbe = HttpProbeService()
        self._ffprobe = FfprobeService(ffprobePath=ffprobePath) if ffprobePath else FfprobeService()
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
        processedBatches = 0
        batchNumber = 0
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

            # Pre-count the total number of batches for progress reporting.
            totalBatches = await self._estimateBatches(targetIds)

            while True:
                if targetIds is None:
                    iterator = self._channelBatches(sm, CHANNEL_BATCH_SIZE)
                else:
                    iterator = self._channelsByIds(sm, targetIds, CHANNEL_BATCH_SIZE)

                probed, batches, batchNumber = await self._probeAll(iterator, totalBatches, batchNumber)
                totalProbed += probed
                processedBatches += batches

                # Drain any on-demand IDs that arrived while we were running.
                if not self._queuedChannelIds:
                    break
                targetIds = set(self._queuedChannelIds)
                self._queuedChannelIds.clear()

            if processedBatches == 0 or totalProbed == 0:
                logger.info("[Reachability] Check finished: no URLs to probe")
                appEventBus.statusBarProgressUpdate.emit("Reachability check finished: no URLs to probe")
            else:
                elapsed = time.monotonic() - probeStartedAt
                logger.info(
                    "Reachability Check complete: %d URL(s) in %d batch(es), done in %.1fs",
                    totalProbed,
                    processedBatches,
                    elapsed,
                )
                appEventBus.statusBarProgressUpdate.emit(
                    f"Reachability check complete. {processedBatches} batch(es), {totalProbed} URL(s) in {elapsed:.1f}s"
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

    async def _estimateBatches(self, targetIds: set[int] | None) -> int:
        """Estimate the total batch count and emit the start progress message.

        Periodic sweeps (``targetIds is None``) count all channels via the
        service; on-demand runs use the given ID set directly.
        """
        if targetIds is None:
            channelCount = await self._channelService.getAllChannelsCount()
            totalBatches = math.ceil(channelCount / CHANNEL_BATCH_SIZE) if channelCount > 0 else 0
        else:
            totalBatches = math.ceil(len(targetIds) / CHANNEL_BATCH_SIZE)

        if totalBatches > 0:
            logger.info("Starting reachability check: %d estimated batch(es)", totalBatches)
            appEventBus.statusBarProgressUpdate.emit(f"Starting reachability check. {totalBatches} batch(es)")
        else:
            logger.info("Starting reachability check: no channels to probe")
            appEventBus.statusBarProgressUpdate.emit("Starting reachability check...")
        return totalBatches

    async def _probeAll(
        self,
        iterator: AsyncIterator[list[Channel]],
        totalExpectedBatches: int = 0,
        batchOffset: int = 0,
    ) -> tuple[int, int, int]:
        """Iterate channel batches, probe each and persist the results.

        Returns ``(totalProbed, totalBatches, batchNumber)`` so the caller can log a
        summary and continue batch numbering across passes. Progress is also
        emitted on the status bar event bus at the start of every batch.
        Every batch is released — ``del`` + ``gc.collect()`` + ``trimHeap()`` —
        right after its results are written to the DB.
        """
        totalProbed = 0
        totalBatches = 0
        batchNumber = batchOffset
        async for batchChannels in iterator:
            totalBatches += 1
            batchNumber += 1

            batchChannelIds = {channel.id for channel in batchChannels}

            results, urlToChannelIds = await self._processBatch(batchNumber, totalExpectedBatches, batchChannels)
            totalProbed += len(results)

            await self._persistBatch(batchChannelIds, results, urlToChannelIds)

            del batchChannels
            del results
            del urlToChannelIds
            del batchChannelIds
            gc.collect()
            trimHeap()
            # Yield to the Qt event loop so queued deleteLater() deletions
            # (QNetworkReply, QProcess) are actually processed between batches;
            # otherwise reply wrappers pile up until the whole run finishes.
            await asyncio.sleep(0)
            # Recreate the QNAM between batches to drop its retained DNS / SSL /
            # keep-alive state, which outlives individual replies. Only safe now
            # that every probe in this batch has resolved and been released.
            self._httpProbe.reset()
        return totalProbed, totalBatches, batchNumber

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
        batchNumber: int,
        totalBatches: int,
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

        appEventBus.statusBarProgressUpdate.emit(f"Starting batch {batchNumber} of total {totalBatches}.")

        logger.info(
            "Starting batch %d of total %d. channel(s): %d -> unique URL(s): %d ",
            batchNumber,
            totalBatches,
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
