#!/usr/bin/env python3
"""Sync tool.pyside6-project.files in pyproject.toml by scanning src/bingr/."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "bingr"
PYPROJECT = ROOT / "pyproject.toml"

INCLUDE_EXTS = {".py", ".qml", ".ui.qml", ".qrc"}
EXCLUDE_DIRS = {"poc", "__pycache__"}
EXCLUDE_PATTERNS = {"* copy.*"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if any(path.match(pat) for pat in EXCLUDE_PATTERNS):
        return False
    return path.suffix in INCLUDE_EXTS or path.name == "qmldir"


def collect_files() -> list[str]:
    files = []
    for f in SRC.rglob("*"):
        if f.is_file() and should_include(f):
            rel = f.relative_to(ROOT)
            files.append(str(rel).replace("\\", "/"))
    return sorted(files)


def make_files_block(paths: list[str]) -> str:
    lines = ['[tool.pyside6-project]']
    lines.append('files = [')
    for p in paths:
        lines.append(f'    "{p}",')
    lines.append(']')
    return '\n'.join(lines)


def main() -> int:
    if not PYPROJECT.exists():
        print(f"ERROR: {PYPROJECT} not found", file=sys.stderr)
        return 1

    files = collect_files()
    print(f"Found {len(files)} files")

    text = PYPROJECT.read_text()

    new_block = make_files_block(files)

    text, n = re.subn(
        r'\[tool\.pyside6-project\].*?(?=\n\[|\Z)',
        new_block,
        text,
        count=1,
        flags=re.DOTALL,
    )

    if n == 0:
        print("ERROR: [tool.pyside6-project] section not found", file=sys.stderr)
        return 1

    PYPROJECT.write_text(text)
    print("Updated pyproject.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())