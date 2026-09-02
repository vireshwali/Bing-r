from types import SimpleNamespace

API_COUNTRIES = [
    {"code": "BA", "name": "Bosnia and Herzegovina", "flag": ""},
    {"code": "HR", "name": "Croatia", "flag": ""},
    {"code": "UK", "name": "United Kingdom", "flag": ""},
]

API_CHANNELS = [
    {
        "id": "BHT1.ba",
        "name": "BHT 1",
        "country": "BA",
        "categories": ["news"],
        "alt_names": [],
        "website": "https://bht.ba",
    },
]

API_FEEDS = [
    {
        "id": "SD",
        "channel": "BHT1.ba",
        "name": "BHT 1 SD",
        "format": "576i",
        "is_main": False,
        "broadcast_area": ["c/BA"],
        "languages": ["bos"],
        "timezones": [],
    },
    {
        "id": "HD",
        "channel": "BHT1.ba",
        "name": "BHT 1 HD",
        "format": "1080p",
        "is_main": True,
        "broadcast_area": ["c/BA"],
        "languages": ["bos"],
        "timezones": [],
    },
]

API_STREAMS = [
    {
        "channel": "BHT1.ba",
        "feed": "SD",
        "url": "http://example.com/sd",
        "quality": "576i",
        "label": "SD",
    },
    {
        "channel": "BHT1.ba",
        "feed": "HD",
        "url": "http://example.com/hd",
        "quality": "1080p",
        "label": "HD",
    },
]

API_CATEGORIES = [
    {"id": "news", "name": "News", "description": "News channels"},
]

API_LANGUAGES = [
    {"code": "bos", "name": "Bosnian"},
]

API_SUBDIVISIONS = [
    {"code": "BA-BIH", "name": "Federation of Bosnia and Herzegovina", "country": "BA"},
]

API_REGIONS = [
    {"code": "EU", "name": "Europe"},
]

API_CITIES = [
    {"code": "Sarajevo", "name": "Sarajevo", "country": "BA"},
]


def segment(**kw) -> SimpleNamespace:
    rawTitle = kw.pop("rawTitle", "BHT 1")
    extinfProps = kw.pop("extinfProps", {})
    flags = kw.pop("flags", [])
    resolution = kw.pop("resolution", None)
    seg = SimpleNamespace(
        title=kw.pop("title", rawTitle),
        uri=kw.pop("uri", "http://example.com/stream"),
        duration=kw.pop("duration", -1.0),
    )
    seg.custom_parser_values = {
        "extra": {
            "raw_title": rawTitle,
            "resolution": resolution,
            "flags": flags,
            "extinf_props": extinfProps,
        }
    }
    return seg
