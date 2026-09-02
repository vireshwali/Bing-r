"""Unit tests for auditService — AuditCategory constants and auditLog() writes."""

from unittest.mock import MagicMock

import pytest

from bingr.db.models import AuditLog
from bingr.services import auditService
from bingr.services.auditService import AuditCategory, auditLog


class TestAuditCategory:
    def testAllConstantsAreLowercaseSnakeCaseStrings(self):
        names = [n for n in dir(AuditCategory) if n.isupper()]
        assert len(names) >= 16
        for name in names:
            value = getattr(AuditCategory, name)
            assert isinstance(value, str)
            assert value
            assert value == value.lower()
            assert "_" in value

    def testCategoryValuesAreUnique(self):
        values = [getattr(AuditCategory, n) for n in dir(AuditCategory) if n.isupper()]
        assert len(values) == len(set(values))


class TestAuditLog:
    @pytest.fixture
    def mockDb(self, mocker):
        """Patch DatabaseManager.get_sessionmaker to a mock session factory."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = mocker.AsyncMock()
        session.__aenter__ = mocker.AsyncMock(return_value=session)
        session.__aexit__ = mocker.AsyncMock(return_value=False)

        sm = MagicMock(return_value=session)
        mocker.patch.object(auditService.DatabaseManager, "get_sessionmaker", return_value=sm)
        return sm, session

    async def testWritesCommittedRow(self, mockDb):
        sm, session = mockDb

        entry = await auditLog(AuditCategory.APP_STARTED, "app booted")

        sm.assert_called_once_with()
        session.add.assert_called_once()
        saved = session.add.call_args[0][0]
        assert isinstance(saved, AuditLog)
        assert saved.category == AuditCategory.APP_STARTED
        assert saved.message == "app booted"
        assert saved.details is None
        assert saved.reason is None
        assert saved.shared is False
        session.commit.assert_awaited_once()
        assert entry is saved

    async def testFullPayloadRoundTrip(self, mockDb):
        _sm, session = mockDb
        details = {"url": "https://example.com/a.m3u8", "code": 404}

        await auditLog(
            AuditCategory.SOURCE_FAILED,
            "import failed",
            details=details,
            reason="bad playlist",
            shared=True,
        )

        saved = session.add.call_args[0][0]
        assert saved.category == AuditCategory.SOURCE_FAILED
        assert saved.details == details
        assert saved.reason == "bad playlist"
        assert saved.shared is True
