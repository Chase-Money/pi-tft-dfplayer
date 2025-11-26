"""Touch calibration utility.

Provides four-point calibration workflow for resistive touchscreens.
"""

import logging
import statistics
import time
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
    """Run four-point touch calibration.

    Args:
        touch: TouchInput instance
        framebuffer: Framebuffer instance
        font: Font for drawing text (optional)

    Returns:
        tuple: (minx, maxx, miny, maxy) calibration values or None if cancelled
    """
    if font is None:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except Exception:
            font = ImageFont.load_default()

    # Calibration target points
    width, height = framebuffer.width, framebuffer.height
    targets = [
        (20, 20),                # Top-left
        (width - 20, 20),        # Top-right
        (width - 20, height - 20), # Bottom-right
        (20, height - 20),       # Bottom-left
    ]

    raw_points = []

    # Collect touches at each target
    for tx, ty in targets:
        # Draw target
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Crosshair
        draw.ellipse((tx - 6, ty - 6, tx + 6, ty + 6), fill=(255, 255, 0))
        draw.line((tx - 20, ty, tx + 20, ty), fill=(255, 255, 0))
        draw.line((tx, ty - 20, tx, ty + 20), fill=(255, 255, 0))

        # Instructions
        draw.text((10, height - 24), "Tap target (hold ~0.5s)...", font=font, fill=(220, 220, 220))

        framebuffer.push(img)

        # Wait for touch
        result = touch.wait_touch_median(timeout=30.0, samples=18)

        if result is None:
            logger.warning("Calibration cancelled (timeout)")
            return None

        raw_points.append(result)
        logger.debug(f"Calibration point {len(raw_points)}: {result}")

    # Calculate calibration bounds
    try:
        cal_bounds = _calculate_calibration(raw_points, touch)
        logger.info(f"Calibration complete: {cal_bounds}")
        return cal_bounds

    except Exception as e:
        logger.error(f"Calibration calculation failed: {e}")
        return None


def _calculate_calibration(
    raw_points: list,
    touch: TouchInput
) -> Tuple[int, int, int, int]:
    """Calculate calibration bounds from raw touch points.

    Args:
        raw_points: List of 4 raw (x, y) touch coordinates
        touch: TouchInput instance (for orientation and driver ranges)

    Returns:
        tuple: (minx, maxx, miny, maxy) calibration bounds
    """
    # Get current orientation settings
    orient = touch.ORIENTATIONS[touch.orientation_index]

    # Invert orientation transforms to get driver axes
    def invert_orientation(rx, ry):
        x, y = rx, ry

        if orient["flip_y"]:
            y = (touch.driver_miny + touch.driver_maxy) - y

        if orient["flip_x"]:
            x = (touch.driver_minx + touch.driver_maxx) - x

        if orient["swap_xy"]:
            x, y = y, x

        return x, y

    # Invert all points
    inverted = [invert_orientation(rx, ry) for rx, ry in raw_points]

    # Calculate bounds from inverted points
    # Points are: top-left, top-right, bottom-right, bottom-left
    left_x = int(statistics.median([inverted[0][0], inverted[3][0]]))
    right_x = int(statistics.median([inverted[1][0], inverted[2][0]]))
    top_y = int(statistics.median([inverted[0][1], inverted[1][1]]))
    bottom_y = int(statistics.median([inverted[2][1], inverted[3][1]]))

    # Ensure valid ranges
    if right_x <= left_x:
        right_x = left_x + 1
    if bottom_y <= top_y:
        bottom_y = top_y + 1

    return (left_x, right_x, top_y, bottom_y)
