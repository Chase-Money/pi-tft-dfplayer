"""v2 UI view helpers for 128x128 layout.

These helpers encapsulate small, single-purpose drawing operations used by
the button-driven 1.44" variant. They intentionally depend on PIL and are
kept lean and composable.
"""

from __future__ import annotations

from typing import Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - allow import without PIL in non-device envs
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore
    PIL_AVAILABLE = False

from src.ui.draw_utils import xywh_to_xyxy, clamp
from src.utils.metadata import load_artwork_thumbnail


def draw_play_indicator(draw, playing: bool, pos: Tuple[int, int], font, color=(230, 230, 230)) -> None:
    if not PIL_AVAILABLE:
        return
    icon = "▶" if playing else "❚❚"
    draw.text(pos, icon, font=font, fill=color)


def draw_track_number(draw, number: int, pos: Tuple[int, int], font, color=(230, 230, 230)) -> None:
    if not PIL_AVAILABLE:
        return
    draw.text(pos, f"{number:03d}", font=font, fill=color)


def draw_artwork_panel(canvas: Image.Image, draw, artwork_path: Optional[str], rect_xywh: Tuple[int, int, int, int]) -> None:
    if not PIL_AVAILABLE:
        return
    x, y, w, h = rect_xywh
    draw.rectangle((x - 2, y - 2, x + w + 2, y + h + 2), fill=(32, 34, 46))

    if not artwork_path:
        return
    thumb = load_artwork_thumbnail(artwork_path, size=(w, h))
    if thumb:
        canvas.paste(thumb, (x, y))


def draw_title_line(draw, title: str, pos: Tuple[int, int], font, max_chars: int = 16, color=(235, 235, 235)) -> None:
    if not PIL_AVAILABLE:
        return
    draw.text(pos, (title or "")[:max_chars], font=font, fill=color)


def draw_volume_bar(draw, volume: int, rect_xywh: Tuple[int, int, int, int], bg=(55, 60, 75), fg=(230, 195, 80)) -> None:
    if not PIL_AVAILABLE:
        return
    x, y, w, h = rect_xywh
    v = clamp(int(volume), 0, 30)
    draw.rectangle(xywh_to_xyxy((x, y, w, h)), fill=bg)
    fillw = int((w) * v / 30)
    draw.rectangle(xywh_to_xyxy((x, y, fillw, h)), fill=fg)


def draw_status_banner(draw, text: str, width: int, fonts, level: str = "info") -> None:
    if not PIL_AVAILABLE or not text:
        return
    colors = {
        "info": ((30, 45, 65), (215, 225, 235)),
        "warning": ((90, 65, 25), (255, 235, 190)),
        "error": ((90, 32, 32), (255, 205, 205)),
        "success": ((30, 70, 45), (210, 240, 210)),
    }
    bg, fg = colors.get(level, colors["info"])
    draw.rectangle((0, 0, width, 32), fill=bg)
    font = fonts.get("small") if isinstance(fonts, dict) else None
    draw.text((12, 8), text, font=font, fill=fg)
