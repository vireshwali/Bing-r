#!/usr/bin/env bash
# Generate flatpak/requirements.txt from uv lockfile for Flatpak pip module.
# Run from project root: scripts/generate-flatpak-deps.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT="$PROJECT_ROOT/flatpak/requirements.txt"

mkdir -p "$PROJECT_ROOT/flatpak"

echo "# Auto-generated from uv.lock — do not edit manually" > "$OUT"
echo "# Regenerate: scripts/generate-flatpak-deps.sh" >> "$OUT"
echo "" >> "$OUT"

# Extract pinned deps from uv.lock for runtime dependencies only.
# --no-dev: exclude the dev toolchain (nuitka, ruff, patchelf,
# nodejs-wheel-binaries, pytest chain).
# The PySide6 umbrella + essentials/addons + shiboken6 are provided by
# io.qt.PySide.BaseApp — never pip-install them on top of it (ABI mismatch
# with the runtime Qt 6.10/6.11). BUT keep pyside6-ds: the app's QML imports
# QtQuick.Studio.DesignEffects (28 files), which ships only in pyside6-ds
# and is NOT present in the BaseApp.
uv export --no-hashes --frozen --no-dev \
  | grep -viE '^(pyside6==|pyside6-essentials==|pyside6-addons==|shiboken6)' \
  | grep -vE '^(ruff|pytest|pyright|basedpyright|coverage|pip|setuptools|wheel|build)' \
  | grep -vE '^-|^#|^$' \
  | grep -E '^[a-zA-Z0-9_.-]+==' \
  >> "$OUT"

echo "Written to $OUT ($(wc -l < "$OUT") lines)"