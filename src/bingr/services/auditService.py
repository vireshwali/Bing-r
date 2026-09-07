"""Audit log service — writes structured event records to the audit_logs table.

Importable from any layer (controller, service, UI handler).  A single async
function ``auditLog()`` that opens its own session, writes, commits - no
caller-side session management needed.
"""

from __future__ import annotations

import logging

from bingr.db.dbManager import DatabaseManager
from bingr.db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditCategory:
    """Canonical event categories for the audit_logs table.

    Naming convention:  <domain>_<action>
    Extend freely as new features are added.
    """

    # ── Source / import lifecycle ───────────────────────────────
    SOURCE_ENQUEUED = "source_enqueued"
    SOURCE_PICKED = "source_picked"
    SOURCE_PROCESSED = "source_processed"
    SOURCE_SKIPPED = "source_skipped"
    SOURCE_FAILED = "source_failed"

    # ── Channel / user interactions (future) ──────────────────
    CHANNEL_VIEWED = "channel_viewed"
    CHANNEL_FAVOURITE_ADDED = "channel_favourite_added"
    CHANNEL_FAVOURITE_REMOVED = "channel_favourite_removed"
    CHANNEL_DISABLED = "channel_disabled"
    CHANNEL_ENABLED = "channel_enabled"

    # ── Application lifecycle ─────────────────────────────────
    APP_STARTED = "app_started"
    APP_CRASHED = "app_crashed"
    APP_CONFIG_CHANGED = "app_config_changed"

    # ── EPG ───────────────────────────────────────────────────
    EPG_UPDATED = "epg_updated"
    EPG_FAILED = "epg_failed"

    # ── System health ─────────────────────────────────────────
    NETWORK_STATUS = "network_status"
    DISK_STATUS = "disk_status"
    RAM_STATUS = "ram_status"


async def auditLog(
    category: str,
    message: str,
    details: dict | None = None,
    reason: str | None = None,
    shared: bool = False,
) -> AuditLog:
    """Write a single entry to the audit_logs table.

    Opens its own session via ``DatabaseManager.get_sessionmaker()``,
    writes the record, and commits.  Safe to call from any async context.
    """
    sm = DatabaseManager.get_sessionmaker()
    async with sm() as session:
        entry = AuditLog(
            category=category,
            message=message,
            details=details,
            reason=reason,
            shared=shared,
        )
        session.add(entry)
        await session.commit()
        logger.debug("auditLog: %s — %s", category, message[:80])
        return entry
