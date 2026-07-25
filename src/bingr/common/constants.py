"""App-wide constants: config keys, API file definitions, etc."""


class KEYS:
    WORKSPACE_PATH = "workspace.path"
    DB_PATH = "db.path"
    LOG_LEVEL = "log.level"
    FILE_CACHE_TTL = "file.cache.ttl"
    DOWNLOAD_TIMEOUT = "download.timeout"
    DATA_CACHE_TTL = "data.cache.ttl"


API_FILES: dict[str, tuple[str, str]] = {
    "channels": ("iptv-org-channels.json", "https://iptv-org.github.io/api/channels.json"),
    "feeds": ("iptv-org-feeds.json", "https://iptv-org.github.io/api/feeds.json"),
    "streams": ("iptv-org-streams.json", "https://iptv-org.github.io/api/streams.json"),
    "countries": ("countries.json", "https://iptv-org.github.io/api/countries.json"),
    "categories": ("categories.json", "https://iptv-org.github.io/api/categories.json"),
    "languages": ("languages.json", "https://iptv-org.github.io/api/languages.json"),
    "subdivisions": ("subdivisions.json", "https://iptv-org.github.io/api/subdivisions.json"),
    "regions": ("regions.json", "https://iptv-org.github.io/api/regions.json"),
    "cities": ("cities.json", "https://iptv-org.github.io/api/cities.json"),
}

# ViewModel roles for targeted event delivery
class ViewModelRole:
    HERO_SECTION = "heroSection"
    GRID = "grid"
    LIST = "list"
