"""Hardware profile selection (v3) with override precedence and auto-detect."""

from __future__ import annotations

import os
from typing import Optional, Tuple


def _norm(profile: Optional[str]) -> Optional[str]:
    if not profile:
        return None
    p = profile.strip().lower()
    if p in ("st7735", "144lcd", "waveshare144", "waveshare_144"):
        return "st7735_buttons"
    if p in ("touch", "ili9486", "tft", "touchscreen"):
        return "ili9486_touch"
    return p


def detect_profile(cli_arg: Optional[str] = None, env: Optional[dict] = None, config=None) -> str:
    env = env or os.environ

    p = _norm(cli_arg)
    if p:
        return p

    p = _norm(env.get("DFPLAYER_HW_PROFILE"))
    if p:
        return p

    if config is not None:
        for key in ("hardware.profile", "hardware_profile"):
            try:
                p = _norm(config.get(key, None))
            except Exception:
                p = None
            if p:
                return p

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
    fb_name_path = "/sys/class/graphics/fb1/name"
    if os.path.exists(fb_name_path):
        name = _read_text(fb_name_path)
        if name and ("ili9486" in name or "ili9" in name):
            return "ili9486_touch"

    hat_prod_path = "/proc/device-tree/hat/product"
    if os.path.exists(hat_prod_path) and os.path.exists("/dev/spidev0.0"):
        prod = _read_text(hat_prod_path, binary=True)
        if prod and "waveshare" in prod:
            return "st7735_buttons"

    if os.path.exists("/dev/input/touchscreen"):
        return "ili9486_touch"

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

