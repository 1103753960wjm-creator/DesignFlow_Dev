from __future__ import annotations

from typing import Final

CAMERA_VIEW_KEYS_DEFAULT: Final[list[str]] = [
    "main",
    "top",
    "wall",
    "elev_n",
    "elev_s",
    "elev_e",
    "elev_w",
    "corner_ne",
    "corner_nw",
    "corner_se",
    "corner_sw",
]

LEGACY_DEPTH_KEY: Final[str] = "0"


def depth_filename(view_key: str) -> str:
    if view_key == LEGACY_DEPTH_KEY:
        return "depth_0.png"
    return f"depth_{view_key}.png"
