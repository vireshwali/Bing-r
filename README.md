# Bing-r

A modern desktop IPTV and media player/manager built with Python, PySide6, and Qt 6.11 Quick/QML.

Focuses on Live TV, VOD, library management, playback, discovery, and community-style metadata/reviews.

## Requirements

- Python >= 3.12
- uv (package manager)

## Setup

```sh
uv sync --dev
uv pip install -e .
```

## Run

```sh
uv run -m bingr.main
```

## Lint

```sh
ruff check .
ruff check . --fix
```

## License

GNU General Public License v3.0
