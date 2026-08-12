"""Hardware decoding backend detection utilities.

Checks which GPU driver libraries are loadable at runtime and maps them to
mpv ``gpu-hwdec-interop`` backend names. Detection is based purely on library
loadability — no vendor IDs, no mpv/ffmpeg version assumptions — so it stays
valid across mpv upgrades.
"""
