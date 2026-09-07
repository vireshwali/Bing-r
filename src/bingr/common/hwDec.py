"""Hardware decoding backend detection utilities.

Checks which GPU driver libraries are loadable at runtime and returns the
matching mpv ``hwdec`` and ``gpu-hwdec-interop`` option values. Detection is
based purely on library loadability — no vendor IDs, no mpv/ffmpeg version
assumptions — so it stays valid across mpv upgrades.

With ``vo=libmpv``, mpv's default ``gpu-hwdec-interop=auto`` behaves like
``all``: every interop backend (cuda, vaapi, ...) is loaded at GL context
creation, producing spurious ``Cannot load libcuda.so.1`` errors on systems
without the matching drivers. Restricting the interop to a loadable backend
removes that noise. Similarly, ``hwdec=auto-safe`` probes every whitelisted
decoder (nvdec, vaapi, ...) at decode time, which makes ffmpeg try to create
hardware device contexts for drivers that are not present; pinning ``hwdec``
to the detected backend avoids those probes entirely.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
from functools import lru_cache
from typing import NamedTuple

logger = logging.getLogger(__name__)

_VAAPI_LIB_NAMES = ("va", "va-x11", "va-drm", "va-glx", "va-wayland")


class HwDecConfig(NamedTuple):
    """mpv option values for the detected hardware decoding backend."""

    hwdec: str
    interop: str


def _try_load(libName: str) -> bool:
    path = ctypes.util.find_library(libName)
    if not path:
        return False
    try:
        ctypes.CDLL(path)
        return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def cudaAvailable() -> bool:
    """True if the NVIDIA CUDA driver library (libcuda.so.1) is loadable."""
    return _try_load("cuda")


@lru_cache(maxsize=1)
def vaapiAvailable() -> bool:
    """True if at least one VAAPI library is loadable."""
    return any(_try_load(name) for name in _VAAPI_LIB_NAMES)


def getHwDecConfig() -> HwDecConfig:
    """Best mpv hwdec configuration for this machine.

    NVIDIA's ``cuda`` interop / ``nvdec`` decoder pair is preferred when the
    CUDA driver is present; otherwise ``vaapi`` for Intel/AMD. Returns the
    default ``auto-safe`` / ``auto`` pair when nothing was detected, preserving
    mpv's default behavior as a last resort.
    """
    if cudaAvailable():
        logger.debug("Selected mpv hwdec: nvdec (CUDA driver present)")
        return HwDecConfig(hwdec="nvdec", interop="cuda")
    if vaapiAvailable():
        logger.debug("Selected mpv hwdec: vaapi (VAAPI libraries present)")
        return HwDecConfig(hwdec="vaapi", interop="vaapi")
    logger.debug("No CUDA/VAAPI driver libraries detected — leaving hwdec at auto-safe")
    return HwDecConfig(hwdec="auto-safe", interop="auto")
