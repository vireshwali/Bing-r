# Bing-r

[![Release](https://img.shields.io/github/release/vireshwali/Bing-r.svg?style=for-the-badge&logo=github)](https://github.com/vireshwali/Bing-r/releases) &nbsp; [![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=for-the-badge&logo=python)](https://python.org) &nbsp; [![Qt](https://img.shields.io/badge/Qt-6.11-green.svg?style=for-the-badge&logo=qt)](https://qt.io) &nbsp; [![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)

🌐 **Website** (coming soon) | **Discord/Telegram** (coming soon) | **Flatpak** (coming soon) | [Report Issues](https://github.com/vireshwali/Bing-r/issues)

**Bing-r** is a modern desktop IPTV and media player/manager application built with Python, PySide6, and Qt Quick/QML. Designed as a high-performance, desktop-native media client focused on Live TV, VOD, library management, playback, discovery, and community-style metadata/reviews.

**Linux-first** — we believe your workstation should be the command centre for everything: work, play, and entertainment. No more juggling between six browser tabs, a media player, and a terminal. Bing-r brings it all together so you stay in the zone. Windows and macOS builds coming soon.

⚠️ **Note:** Bing-r does not provide any playlists or other digital content. Bing-r is purely a media and content management and playing application platform. The channels and pictures in the screenshots are for demonstration purposes only.

> [!IMPORTANT]
> **Official sources only.** Bing-r is a free, open-source **player** - it never sells IPTV subscriptions, channels, or playlists. Websites offering "Bing-r subscriptions/channels/premium/activated" builds are **not affiliated** with this project or this proejct's authors. <br />
> Get the app only from the [official GitHub repository](https://github.com/vireshwali/Bing-r) or [GitHub Releases](https://github.com/vireshwali/Bing-r/releases).

---

## Features

### Channels Sources
- **M3U-based content manager** — import M3U / M3U8 playlists from local files or remote URLs
- Drag-and-drop file import with instant processing
- URL-based playlist download with automatic updates
- EPG URL parsing from `x-tvg-url` headers

### Playback
- Built-in Qt Multimedia / mpv integration (planned)


### Live TV & EPG
- Channel grid with category/country/quality filters
- Hero carousel for top channels (by visit count)
- EPG / XMLTV TV guide architecture (planned)
- TV archive / catch-up / timeshift (planned)

### Library Management
- SQLite database with SQLAlchemy async ORM
- Automatic channel deduplication and merge across sources
- Visit counting and favorites (planned)
- Recently viewed / watch history (planned)

### Metadata & Enrichment
- **iptv-org** integration — automatic channel lookup by tvg-id. Bing-r works well with iptv-org m3us and has been etsted with other popular content sources as well. As long as the m3us conform to basic m3u formats, it shoudl work well with Bing-r
- Feed/stream matching with scored selection (format, region, name)
- Broadcast area, categories, languages expansion
- Canonical names, alt_names, tags, logos from iptv-org database

### Organization
- Per-source and global channel management
- Category, country, quality filters
- Search across channels using channel names
- Create Playlists and Groups (planned))
- Command palette and keybaord shortcuts(planned)

### Platform
- Cross-platform desktop app backbone. Focused on Linux initially (macOS, Windows planned)
- Native Qt Quick Controls based UI with responsive and fluid feel.
- Dark theme. (Light theme planned)
- Keyboard shortcuts

---

## Screenshots

> **Coming soon** — Screenshots will be added after UI polish.

### Main Channel View
![Bing-r Channels](screenshots/channels-view.png)

### Add Channels / Import
![Bing-r Add Channels](screenshots/add-channels.png)

### Home / Dashboard
![Bing-r Home](screenshots/home.png)

### EPG / TV Guide (Planned)
![Bing-r EPG](screenshots/epg.png)

### Settings
![Bing-r Settings](screenshots/settings.png)

---

## Installation

### From Source (Recommended)

```bash
# Prerequisites: Python 3.12+, uv (or pip)
git clone https://github.com/vireshwali/Bing-r.git
cd Bing-r

# Install dependencies
uv sync --all-groups

# Run the application
uv run -m bingr.main
```

### Development Setup

```bash
# Install with development dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint & format
ruff check . --fix

# Type check
uv run basedpyright
```

### Packaged Builds (Planned)
- Linux: AppImage, Flatpak, Snap

Planned Later
- macOS: .dmg (signed/notarized)
- Windows: .exe installer, MSIX

---

## Usage

### Adding Playlists
1. Open **Add Channels** from the left navigation
2. **Drag & drop** `.m3u`/`.m3u8` files, or
3. **Paste URLs** (up to 4) in the URL input fields
4. Click **Add URLs** or wait for file processing
5. Channels appear in the **Channels** screen automatically

### Navigating Channels
- **Home** — Dashboard with quick actions
- **Channels** — Full channel grid with filters (category, country, quality)
- **Favourites** — Your favorite channels (planned)
- **Playlists** — Manage imported sources (planned)

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd+K` | Open command palette (planned) |
| `Ctrl/Cmd+F` | Focus search |
| `Space` | Play/pause (when player active) |
| `F` | Toggle fullscreen (when player active) |
| `M` | Mute |
| `?` | Show shortcuts help (planned) |

---

## Development

### Architecture Overview
```
src/bingr/
├── main.py                    # App entry: splash -> async init -> App.qml
├── controllers/               # QML singleton controllers (Python <-> QML bridge)
├── services/                  # Import, enrichment, EPG, channel management
├── ui/                        # QML screens & reusable components
├── ui_models/                 # QAbstractListModel view models for QML
├── db/                        # SQLAlchemy models, manager, migrations
└── common/                    # Config, cache, logging, event bus
```

### Key Technologies
- **UI**: PySide6 6.11 + Qt Quick Controls 2 + Qt Quick Layouts
- **Database**: SQLAlchemy 2.0 (async) + aiosqlite + Alembic
- **Playlist**: m3u8 parser with custom EXTINF attribute handling
- **Metadata**: iptv-org API data (channels, feeds, streams, categories, countries)
- **Async**: asyncio + PySide6.QtAsyncio integration
- **Testing**: pytest + pytest-asyncio

### Running Tests
```bash
# All tests
uv run pytest

# Unit only
uv run pytest tests/unit -v

# Integration only
uv run pytest tests/integration -v

# With coverage
uv run pytest --cov=src/bingr --cov-report=html
```

### Code Quality
```bash
# Lint & auto-fix
ruff check . --fix

# Format only
ruff format .

# Type check
uv run basedpyright
```

### Adding QML Components
1. Create `.ui.qml` in `src/bingr/ui/Components/`
2. Register in `src/bingr/ui/Components/qmldir`
3. Import in screens via `import "../Components"`

---

## Disclaimer

**Bing-r doesn't provide any playlists or other digital content.**

Bing-r is a **player application only** — it does not sell, host, or distribute IPTV subscriptions, channels, playlists, or any copyrighted content. Users are responsible for the content they choose to play through the application.

Websites or services offering "Bing-r subscriptions," "Bing-r channels," "Bing-r premium," or "activated builds" are **not affiliated** with this project. Download Bing-r only from the [official GitHub repository](https://github.com/vireshwali/Bing-r) or [official releases](https://github.com/vireshwali/Bing-r/releases).

Bing-r uses Qt and PySide6 under the LGPL v3 license. This is a non-commercial, open-source project. For commercial licensing inquiries, refer to the [Qt Licensing](https://www.qt.io/licensing/) page.

---

## Trademark

The name **"Bing-r"** and the Bing-r logo are trademarks of the project owner. The MIT license covers the **source code only** — it does **not** grant rights to the name or logo. Forks and redistributions (including app-store submissions) must use a different name and their own icon.

---

## Credits & Attributions

### Core Dependencies
- **[Qt 6](https://qt.io)** — Cross-platform application framework (LGPL v3 / Commercial)
- **[PySide6](https://wiki.qt.io/Qt_for_Python)** — Official Python bindings for Qt (LGPL v3)
- **[SQLAlchemy](https://sqlalchemy.org)** — Python SQL toolkit (MIT)
- **[Alembic](https://alembic.sqlalchemy.org)** — Database migrations (MIT)
- **[aiosqlite](https://github.com/omnilib/aiosqlite)** — Async SQLite driver (MIT)
- **[httpx](https://httpx.org)** — Modern HTTP client (BSD-3)
- **[lxml](https://lxml.de)** — XML/HTML processing (BSD)
- **[m3u8](https://github.com/globocom/m3u8)** — M3U8 playlist parser (MIT)
- **[orjson](https://github.com/ijl/orjson)** — Fast JSON (MIT / Apache-2.0)
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — Environment config (BSD-3)

### Data Sources
- **[iptv-org](https://github.com/iptv-org)** — Channel / feed / stream metadata database (MIT)
  Channels, feeds, streams, categories, countries, languages, regions, cities, subdivisions — used for automatic playlist enrichment and EPG matching.

### Icons & Assets
- Icons from various open-source icon sets (sources TBD)
- Splash screen background (TBD)

### Inspiration & Reference
- **[IPTVnator](https://github.com/4gray/iptvnator)** — Feature reference & README structure

---

## License
Refer the License file for extended licensing terms.

---

## Contributing

Contributions are welcome! Please read our contributing guidelines (coming soon) before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

---

## Support

- **Issues**: [GitHub Issues](https://github.com/vireshwali/Bing-r/issues)
- **Discussions**: [GitHub Discussions](https://github.com/vireshwali/Bing-r/discussions)
- **Security**: Email security concerns to [security@vireshwali.dev](mailto:security@vireshwali.dev)

---

*Built with ❤️ using Python, Qt, and open-source*