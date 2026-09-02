"""Unit tests for SystemHealthMonitorService — internet/disk/RAM checks and event-bus output.

``httpx.Client``, ``shutil.disk_usage`` and the ``/proc/meminfo`` read are mocked
out; the status-bar event-bus signals are patched with mocks so emissions can be
asserted without a Qt event loop. Also verifies the change-detection dedup: a
status message is only emitted when the underlying state actually flips.
"""

import asyncio
from types import SimpleNamespace

import pytest

from bingr.common.eventBus import appEventBus
from bingr.services.systemHealthMonitorService import SystemHealthMonitorService

_GB = 1024**3


@pytest.fixture
def service(tmp_path):
    return SystemHealthMonitorService(tmp_path)


@pytest.fixture
def bus(mocker):
    """Mock the status-bar event-bus signals so emissions are recorded."""
    return {
        "progress": mocker.patch.object(appEventBus, "statusBarProgressUpdate"),
        "internet": mocker.patch.object(appEventBus, "statusBarInternetUpdate"),
        "disk": mocker.patch.object(appEventBus, "statusBarDiskUpdate"),
        "ram": mocker.patch.object(appEventBus, "statusBarRamUpdate"),
    }


class TestConstruction:
    def testSubscribesToHealthCheckRequest(self, mocker, tmp_path):
        connect = mocker.patch.object(appEventBus, "systemHealthCheckRequested")
        SystemHealthMonitorService(tmp_path)
        connect.connect.assert_called_once()

    def testTracksLastStatusesAsNoneInitially(self, service):
        assert service._lastOnline is None
        assert service._lastDiskStatus is None
        assert service._lastRamStatus is None


class TestRunAllChecksOnDemand:
    async def testSpawnsAllThreeChecks(self, service, bus, mocker):
        for name in ("_checkInternet", "_checkDisk", "_checkRam"):
            mocker.patch.object(service, name, new=mocker.AsyncMock())

        service.runAllChecksOnDemand()
        await asyncio.sleep(0)

        service._checkInternet.assert_awaited_once()
        service._checkDisk.assert_awaited_once()
        service._checkRam.assert_awaited_once()
        bus["progress"].emit.assert_any_call("Checking system health...")


class TestInternet:
    def _setStatus(self, mocker, code):
        client = mocker.patch("bingr.services.systemHealthMonitorService.httpx.Client")
        # The service uses `with httpx.Client(...) as client:` — MagicMock's
        # __enter__ returns a separate child mock, so configure get() there.
        client.return_value.__enter__.return_value.get.return_value.status_code = code
        return client

    async def testOnlineEmitsSuccessOnChange(self, service, bus, mocker):
        self._setStatus(mocker, 204)

        await service._checkInternet()

        bus["internet"].emit.assert_called_once_with("Internet connected and good", "success")
        assert service._lastOnline is True

    async def testOfflineEmitsErrorOnChange(self, service, bus, mocker):
        self._setStatus(mocker, 503)

        await service._checkInternet()

        bus["internet"].emit.assert_called_once_with("No internet connection", "error")
        assert service._lastOnline is False

    async def testNoEmitWhenStatusUnchanged(self, service, bus, mocker):
        self._setStatus(mocker, 204)

        await service._checkInternet()
        await service._checkInternet()

        bus["internet"].emit.assert_called_once()

    async def testEmitsOnEachTransition(self, service, bus, mocker):
        client = self._setStatus(mocker, 204)
        await service._checkInternet()

        client.return_value.__enter__.return_value.get.return_value.status_code = 503
        await service._checkInternet()

        assert bus["internet"].emit.call_count == 2
        assert bus["internet"].emit.call_args_list[0].args == ("Internet connected and good", "success")
        assert bus["internet"].emit.call_args_list[1].args == ("No internet connection", "error")

    async def testExceptionTreatsAsOffline(self, service, bus, mocker):
        client = mocker.patch("bingr.services.systemHealthMonitorService.httpx.Client")
        client.side_effect = RuntimeError("network down")

        await service._checkInternet()

        bus["internet"].emit.assert_called_once_with("No internet connection", "error")
        assert service._lastOnline is False


class TestDisk:
    def _setFree(self, mocker, freeGb):
        mocker.patch(
            "bingr.services.systemHealthMonitorService.shutil.disk_usage",
            return_value=SimpleNamespace(free=freeGb * _GB),
        )

    async def testGreenEmitsSuccess(self, service, bus, mocker):
        self._setFree(mocker, 15)

        await service._checkDisk()

        bus["disk"].emit.assert_called_once_with("Disk space is good.", "success")
        assert service._lastDiskStatus == "green"

    async def testYellowEmitsWarning(self, service, bus, mocker):
        self._setFree(mocker, 7)

        await service._checkDisk()

        bus["disk"].emit.assert_called_once_with("Disk space is low: 7.0GB free", "warning")
        assert service._lastDiskStatus == "yellow"

    async def testRedEmitsError(self, service, bus, mocker):
        self._setFree(mocker, 2)

        await service._checkDisk()

        bus["disk"].emit.assert_called_once_with("Critically low disk space: 2.0GB free", "error")
        assert service._lastDiskStatus == "red"

    async def testBoundaries(self, service, bus, mocker):
        self._setFree(mocker, 10)
        await service._checkDisk()
        assert service._lastDiskStatus == "green"

        self._setFree(mocker, 9.999)
        await service._checkDisk()
        assert service._lastDiskStatus == "yellow"

    async def testNoEmitWhenUnchanged(self, service, bus, mocker):
        self._setFree(mocker, 15)

        await service._checkDisk()
        await service._checkDisk()

        bus["disk"].emit.assert_called_once()

    async def testExceptionSkipsEmit(self, service, bus, mocker):
        mocker.patch(
            "bingr.services.systemHealthMonitorService.shutil.disk_usage",
            side_effect=OSError("stat failed"),
        )

        await service._checkDisk()

        bus["disk"].emit.assert_not_called()
        assert service._lastDiskStatus is None


class TestRam:
    async def testGreenEmitsSuccess(self, service, bus, mocker):
        mocker.patch.object(service, "_getAvailableRamGb", return_value=2.5)

        await service._checkRam()

        bus["ram"].emit.assert_called_once_with("System memory is sufficient", "success")
        assert service._lastRamStatus == "green"

    async def testYellowEmitsWarning(self, service, bus, mocker):
        mocker.patch.object(service, "_getAvailableRamGb", return_value=1.5)

        await service._checkRam()

        bus["ram"].emit.assert_called_once_with("System memory is low: 1.5GB free", "warning")
        assert service._lastRamStatus == "yellow"

    async def testRedEmitsError(self, service, bus, mocker):
        mocker.patch.object(service, "_getAvailableRamGb", return_value=0.8)

        await service._checkRam()

        bus["ram"].emit.assert_called_once_with("Critical system memory: 0.8GB free", "error")
        assert service._lastRamStatus == "red"

    async def testBoundaries(self, service, bus, mocker):
        mocker.patch.object(service, "_getAvailableRamGb", return_value=1.8)
        await service._checkRam()
        assert service._lastRamStatus == "green"

        mocker.patch.object(service, "_getAvailableRamGb", return_value=1.2)
        await service._checkRam()
        assert service._lastRamStatus == "yellow"

    async def testNoEmitWhenUnchanged(self, service, bus, mocker):
        mocker.patch.object(service, "_getAvailableRamGb", return_value=2.5)

        await service._checkRam()
        await service._checkRam()

        bus["ram"].emit.assert_called_once()


class TestGetAvailableRamGb:
    def testReadsMemAvailableFromProc(self, tmp_path, mocker):
        mocker.patch(
            "builtins.open",
            mocker.mock_open(read_data="MemTotal:       1000 kB\nMemAvailable:    800 kB\nMemFree:        500 kB\n"),
        )

        svc = SystemHealthMonitorService(tmp_path)

        assert svc._getAvailableRamGb() == pytest.approx(800 / (1024**2))

    def testMissingMemAvailableReturnsZero(self, tmp_path, mocker):
        mocker.patch("builtins.open", mocker.mock_open(read_data="MemTotal: 1000 kB\n"))

        svc = SystemHealthMonitorService(tmp_path)

        assert svc._getAvailableRamGb() == 0.0

    def testOpenFailureReturnsZero(self, tmp_path, mocker):
        mocker.patch("builtins.open", side_effect=OSError("no /proc"))

        svc = SystemHealthMonitorService(tmp_path)

        assert svc._getAvailableRamGb() == 0.0
