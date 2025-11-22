"""UI drawing utilities (v2).

Pure helpers for geometry and text layout, designed for reuse and testing.
These functions avoid hardware and can be unit-tested without PIL.
"""

from __future__ import annotations

from typing import Iterable, Tuple


def xywh_to_xyxy(rect: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """Convert (x, y, w, h) → (x, y, x+w, y+h)."""
    x, y, w, h = rect
    return (x, y, x + w, y + h)


def inside(rect: Tuple[int, int, int, int], px: int, py: int) -> bool:
    """Return True if point (px, py) is inside (x, y, w, h)."""
    x, y, w, h = rect
    return x <= px <= x + w and y <= py <= y + h


def clamp(value: int, lo: int, hi: int) -> int:
    """Clamp integer value into [lo, hi]."""
    return max(lo, min(hi, value))


def iter_lines_by_width(
    words: Iterable[str],
    max_width: int,
    measure: callable,
) -> Iterable[str]:
    """Yield lines by fitting words greedily within max_width.

    `measure(text: str) -> int` should return pixel width. This keeps the
    implementation testable without PIL.
    """
    line = ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if not line:
            line = candidate
            continue
        width = measure(candidate)
        if width <= max_width:
            line = candidate
        else:
            yield line
            line = word
    if line:
        yield line

