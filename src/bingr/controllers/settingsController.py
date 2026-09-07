"""Settings controller — singleton QML bridge for the Settings screen.

Owns one ``SettingsService`` instance, tracks pending (unsaved) changes in a
``{key: value}`` dict, and exposes generic slots plus status signals to QML.
Keeps no per-setting properties — the QML pages read/write through the
generic ``getValue``/``onValueChanged`` API.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement

from bingr.services.settingsService import SettingsService
from bingr.ui_models.settigsModel import SettingsModel

if TYPE_CHECKING:
    from bingr.services.settingsService import SettingsService as SettingsServiceType
else:
    SettingsServiceType = "SettingsService"

QML_IMPORT_NAME = "bingr.controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
class SettingsController(QObject):
    """Bridge between the Settings UI and the QSettings-backed service."""

    loadingChanged = Signal(bool)
    settingsCacheChanged = Signal()
    restartRequiredChanged = Signal(bool)
    saveCompleted = Signal()
    cancelCompleted = Signal()
    resetRequested = Signal()
    resetCompleted = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service: SettingsServiceType = SettingsService()
        self._loading = True
        self._restartRequired: bool = False

    async def _loadSettings(self) -> None:
        model = await self._service.loadAll()
        self._settingsCache = asdict(model)
        self.settingsCacheChanged.emit()

    @Property(bool, notify=restartRequiredChanged)
    def restartRequired(self) -> bool:  # type: ignore
        return self._restartRequired

    @restartRequired.setter
    def restartRequired(self, value: bool) -> None:
        if self._restartRequired != value:
            self._restartRequired = value
            self.restartRequiredChanged.emit(value)

    @Property(bool, notify=loadingChanged)
    def loading(self):  # type: ignore
        return self._loading

    @loading.setter
    def loading(self, value: bool) -> None:
        if self._loading == value:
            return
        self._loading = value
        self.loadingChanged.emit(value)

    @Property(cast(type, "QVariantMap"), notify=settingsCacheChanged)
    def settingsCache(self) -> dict[str, Any]:
        return self._settingsCache

    # ── Value access (generic) ──────────────────────────────────────────

    @Slot()
    def getAllSettings(self):
        self.loading = True  # type: ignore
        # self.restartRequired = False  # type: ignore
        loadTask = asyncio.ensure_future(self._loadSettings())
        loadTask.add_done_callback(
            lambda fut: (
                logger.info("Loading settings data from DB completed."),
                setattr(self, "loading", False),
            )
        )

    @Slot(str, result="QVariant")
    def getValue(self, key: str) -> Any:
        """Return the current (pending-if-unsaved, else stored) value for ``key``."""
        return self._service.get(key)

    @Slot(str, result="QVariant")
    def defaultValue(self, key: str) -> Any:
        return self._service.get(key)

    @Slot(str, "QVariant")
    def onValueChanged(self, key: str, value: Any) -> None:
        """Record a pending change from the UI and flag restart requirement."""
        logger.debug("pending setting %s = %r", key, value)

    # ── Commit / discard ────────────────────────────────────────────────

    @Slot("QVariantMap")
    def save(self, settingsData: dict[str, Any]) -> None:
        """Persist all settings from UI to DB."""
        self.loading = True  # type: ignore
        task = asyncio.ensure_future(self._saveSettingsAsync(settingsData))
        task.add_done_callback(
            lambda fut: (
                setattr(self, "loading", False),
                self.saveCompleted.emit(),
                logger.info("settings save completed"),
            )
        )

    async def _saveSettingsAsync(self, settingsData: dict[str, Any]) -> None:
        """Create SettingsModel from dict, persist to DB, reload cache."""
        model = SettingsModel(**{k: v for k, v in settingsData.items() if hasattr(SettingsModel, k)})
        await self._service.setBulk(model)
        await self._loadSettings()

    @Slot()
    def cancel(self) -> None:
        """Discard all pending changes."""
        self.cancelCompleted.emit()
        logger.info("settings changes discarded")

    # ── Reset flow ──────────────────────────────────────────────────────

    @Slot()
    def requestReset(self) -> None:
        """Ask the UI to confirm a reset via the ConfirmDialog."""
        self.resetRequested.emit()

    @Slot()
    def confirmReset(self) -> None:
        """Reset every setting to defaults."""
        self.loading = True  # type: ignore
        task = asyncio.ensure_future(self._resetAsync())
        task.add_done_callback(
            lambda fut: (
                setattr(self, "loading", False),
                self.resetCompleted.emit(),
                logger.info("settings reset to defaults"),
            )
        )

    async def _resetAsync(self) -> None:
        """Delete all DB rows, reload cache with defaults."""
        await self._service.resetToDefaults()
        await self._loadSettings()
