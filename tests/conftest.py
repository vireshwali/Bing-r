"""Shared test helpers — all runtime artifacts live under tests/_tests_runtime."""

from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = TESTS_ROOT / "_tests_runtime"


@pytest.fixture(scope="session")
def runtimeDir():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR
