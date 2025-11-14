"""Hardware profile selection (v2).

Provides a narrow API to choose display and input classes based on profile.
Testable without hardware via dependency strings.
"""

import os
from typing import Tuple


def detect_profile() -> str:
    # Priority: env var > default
    env = os.environ.get("DFPLAYER_HW_PROFILE")
    if env:
        return env.strip().lower()
    return "ili9486_touch"


def select_hardware(profile: str) -> Tuple[str, str]:
    """Return dotted path strings for (DisplayClass, InputClass)."""
    p = (profile or "").strip().lower()
    if p in ("st7735_buttons", "st7735", "144lcd"):
        return (
            "src.hardware.display_st7735.DisplayST7735",
            "src.hardware.button_input.ButtonInput",
        )
    return (
        "src.hardware.framebuffer.Framebuffer",
        "src.hardware.touch.TouchInput",
    )


def import_by_path(dotted: str):
    module_name, _, attr = dotted.rpartition(".")
    if not module_name:
        raise ImportError(f"Invalid dotted path: {dotted}")
    mod = __import__(module_name, fromlist=[attr])
    return getattr(mod, attr)

