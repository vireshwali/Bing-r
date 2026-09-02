import pytest

from bingr.common.cache import getFileCache
from tests.unit._data import (
    API_CATEGORIES,
    API_CHANNELS,
    API_CITIES,
    API_COUNTRIES,
    API_FEEDS,
    API_LANGUAGES,
    API_REGIONS,
    API_STREAMS,
    API_SUBDIVISIONS,
)


@pytest.fixture(autouse=True)
def clearCache():
    getFileCache().clear()


@pytest.fixture
def apiData(mocker):
    store = {
        "countries": API_COUNTRIES,
        "channels": API_CHANNELS,
        "feeds": API_FEEDS,
        "streams": API_STREAMS,
        "categories": API_CATEGORIES,
        "languages": API_LANGUAGES,
        "subdivisions": API_SUBDIVISIONS,
        "regions": API_REGIONS,
        "cities": API_CITIES,
    }
    mocker.patch.object(
        getFileCache(),
        "load",
        side_effect=lambda name, _store=store: _store.get(name, []),
    )
