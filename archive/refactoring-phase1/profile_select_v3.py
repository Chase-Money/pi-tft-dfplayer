"""Hardware profile selection (v3) with override precedence and auto-detect.

Precedence: CLI flag > environment variable > config file > auto-detect.

Returns dotted class paths for display and input abstractions to keep this
module import-light and easy to test.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


def _norm(profile: Optional[str]) -> Optional[str]:
    if not profile:
        return None
    p = profile.strip().lower()
    # normalize aliases
    if p in ("st7735", "144lcd", "waveshare144", "waveshare_144"):
        return "st7735_buttons"
    if p in ("touch", "ili9486", "tft", "touchscreen"):
        return "ili9486_touch"
    return p


def detect_profile(cli_arg: Optional[str] = None, env: Optional[dict] = None, config=None) -> str:
    """Detect the hardware profile using precedence rules.

    Args:
        cli_arg: Explicit hardware profile from command line.
        env: Environment dict-like; defaults to os.environ.
        config: Optional config object exposing `get(key, default)`.
    """
    env = env or os.environ

    # CLI override
    p = _norm(cli_arg)
    if p:
        return p

    # Environment override
    p = _norm(env.get("DFPLAYER_HW_PROFILE"))
    if p:
        return p

    # Config override (support two keys)
    if config is not None:
        for key in ("hardware.profile", "hardware_profile"):
            try:
                p = _norm(config.get(key, None))
            except Exception:
                p = None
            if p:
                return p

    # Auto-detect
    detected = _auto_detect()
    if detected:
        return detected

    return "unknown"


def _read_text(path: str, binary: bool = False) -> Optional[str]:
    try:
        mode = "rb" if binary else "r"
        with open(path, mode) as f:
            data = f.read()
        if binary and isinstance(data, (bytes, bytearray)):
            return bytes(data).decode("utf-8", "ignore").strip("\x00\n\r ").lower()
        if isinstance(data, str):
            return data.strip().lower()
        return None
    except Exception:
        return None


def _auto_detect() -> Optional[str]:
    # Prefer explicit framebuffer model name for touchscreen path
    fb_name_path = "/sys/class/graphics/fb1/name"
    if os.path.exists(fb_name_path):
        name = _read_text(fb_name_path)
        if name and ("ili9486" in name or "ili9" in name):
            return "ili9486_touch"

    # Waveshare HAT product string + SPI device presence for 1.44" variant
    hat_prod_path = "/proc/device-tree/hat/product"
    if os.path.exists(hat_prod_path) and os.path.exists("/dev/spidev0.0"):
        prod = _read_text(hat_prod_path, binary=True)
        if prod and "waveshare" in prod:
            return "st7735_buttons"

    # Touchscreen presence as a weak indicator
    if os.path.exists("/dev/input/touchscreen"):
        return "ili9486_touch"

    # SPI presence as a weak indicator for ST7735 class devices
    if os.path.exists("/dev/spidev0.0"):
        return "st7735_buttons"

    return None


def select_hardware(profile: str) -> Tuple[str, str]:
    p = _norm(profile) or "ili9486_touch"
    if p == "st7735_buttons":
        return (
            "src.hardware.display_st7735.DisplayST7735",
            "src.hardware.button_input.ButtonInput",
        )
    if p == "ili9486_touch":
        return (
            "src.hardware.framebuffer.Framebuffer",
            "src.hardware.touch.TouchInput",
        )
    # unknown → require explicit selection
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

