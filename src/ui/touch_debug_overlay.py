"""Touch debug visualization overlay."""

import time
from typing import Optional, Tuple
from PIL import ImageDraw

class TouchDebugOverlay:
    """Renders visual debugging information for touch events."""

    def __init__(self):
        self.last_touch_pos: Optional[Tuple[int, int]] = None
        self.last_touch_time: float = 0.0
        self.display_duration = 2.0  # Show crosshairs for 2 seconds

    def record_touch(self, x: int, y: int) -> None:
        """Record a touch event for visualization."""
        self.last_touch_pos = (x, y)
        self.last_touch_time = time.time()

    def render(self, draw: ImageDraw.ImageDraw, font=None) -> None:
        """Render touch debug overlay if recent touch exists."""
        if not self.last_touch_pos:
            return

        # Only show for display_duration seconds
        elapsed = time.time() - self.last_touch_time
        if elapsed > self.display_duration:
            return

        x, y = self.last_touch_pos

        # Get image dimensions from draw object
        width, height = draw.im.size

        # Draw crosshairs (red)
        draw.line((0, y, width, y), fill=(255, 0, 0), width=2)
        draw.line((x, 0, x, height), fill=(255, 0, 0), width=2)

        # Draw circle at touch point
        radius = 10
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     outline=(255, 0, 0), width=3)

        # Draw coordinates (yellow text)
        coord_text = f"Touch: ({x}, {y})"
        text_x = min(x + 15, width - 100)  # Keep text on screen
        text_y = max(y - 20, 10)

        if font:
            draw.text((text_x, text_y), coord_text, font=font, fill=(255, 255, 0))
        else:
            draw.text((text_x, text_y), coord_text, fill=(255, 255, 0))
