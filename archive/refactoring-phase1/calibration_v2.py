"""Touch calibration utility (v2).

Uses absolute imports to avoid parent-relative import errors.
"""

import logging
import statistics
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from hardware.touch import TouchInput
from hardware.framebuffer import Framebuffer

logger = logging.getLogger(__name__)


def run_calibration(
    touch: TouchInput,
    framebuffer: Framebuffer,
    font: Optional[ImageFont.FreeTypeFont] = None
) -> Optional[Tuple[int, int, int, int]]:
    if font is None:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except Exception:
            font = ImageFont.load_default()

    width, height = framebuffer.width, framebuffer.height
    targets = [
        (20, 20), (width - 20, 20), (width - 20, height - 20), (20, height - 20)
    ]

    raw_points = []
    for tx, ty in targets:
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((tx - 6, ty - 6, tx + 6, ty + 6), fill=(255, 255, 0))
        draw.line((tx - 20, ty, tx + 20, ty), fill=(255, 255, 0))
        draw.line((tx, ty - 20, tx, ty + 20), fill=(255, 255, 0))
        draw.text((10, height - 24), "Tap target (hold ~0.5s)...", font=font, fill=(220, 220, 220))
        framebuffer.push(img)

        result = touch.wait_touch_median(timeout=30.0, samples=18)
        if result is None:
            logger.warning("Calibration cancelled (timeout)")
            return None
        raw_points.append(result)

    try:
        cal_bounds = _calculate_calibration(raw_points, touch)
        logger.info(f"Calibration complete: {cal_bounds}")
        return cal_bounds
    except Exception as e:
        logger.error(f"Calibration calculation failed: {e}")
        return None


def _calculate_calibration(raw_points: list, touch: TouchInput) -> Tuple[int, int, int, int]:
    orient = touch.ORIENTATIONS[touch.orientation_index]

    def invert_orientation(rx, ry):
        x, y = rx, ry
        if orient["FLIP_Y"]:
            y = (touch.driver_miny + touch.driver_maxy) - y
        if orient["FLIP_X"]:
            x = (touch.driver_minx + touch.driver_maxx) - x
        if orient["SWAP_XY"]:
            x, y = y, x
        return x, y

    inverted = [invert_orientation(rx, ry) for rx, ry in raw_points]
    left_x = int(statistics.median([inverted[0][0], inverted[3][0]]))
    right_x = int(statistics.median([inverted[1][0], inverted[2][0]]))
    top_y = int(statistics.median([inverted[0][1], inverted[1][1]]))
    bottom_y = int(statistics.median([inverted[2][1], inverted[3][1]]))

    if right_x <= left_x:
        right_x = left_x + 1
    if bottom_y <= top_y:
        bottom_y = top_y + 1

    return (left_x, right_x, top_y, bottom_y)

