#!/usr/bin/env python3
"""Convert QML image references from development paths to QRC paths.

Build-time script for Flatpak packaging.  Replaces Qt.resolvedUrl("images/...")
and bare "images/..." string literals with "qrc:/images/..." so the compiled
QRC resources are found at runtime.

Usage:
    python3 scripts/convert_qrc_refs.py <qml_dir>

Example:
    python3 scripts/convert_qrc_refs.py src/bingr/ui
"""

import re
import sys
from pathlib import Path

# Matches "images/... (any filename)" but NOT "qrc:/images/..." (already converted)
_PATTERN = re.compile(r'"images/([^"]+)"')


def convert_file(path: Path) -> list[tuple[int, str, str]]:
    """Convert image refs in a single QML file.

    Returns list of (line_number, old_line, new_line) for each change.
    """
    lines = path.read_text().splitlines(keepends=True)
    changes: list[tuple[int, str, str]] = []
    new_lines: list[str] = []

    for line_num, line in enumerate(lines, start=1):
        new_line, count = _PATTERN.subn(r'"qrc:/images/\1"', line)
        if count:
            changes.append((line_num, line.rstrip(), new_line.rstrip()))
        new_lines.append(new_line)

    if changes:
        path.write_text("".join(new_lines))

    return changes


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <qml_dir>", file=sys.stderr)
        return 1

    qml_dir = Path(sys.argv[1])
    if not qml_dir.is_dir():
        print(f"Error: {qml_dir} is not a directory", file=sys.stderr)
        return 1

    total = 0
    files_changed = 0

    for qml_file in sorted(qml_dir.rglob("*.qml")):
        changes = convert_file(qml_file)
        if changes:
            files_changed += 1
            total += len(changes)
            rel = qml_file.relative_to(qml_dir.parent.parent)
            print(f"\n  {rel} ({len(changes)} change(s)):")
            for line_num, old, new in changes:
                print(f"    L{line_num}:")
                print(f"      - {old}")
                print(f"      + {new}")

    print(f"\nConverted {total} reference(s) in {files_changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
