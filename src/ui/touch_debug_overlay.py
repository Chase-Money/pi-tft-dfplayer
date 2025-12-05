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

        # Draw crosshairs (bright red, thicker lines for visibility)
        draw.line((0, y, width, y), fill=(255, 0, 0), width=3)
        draw.line((x, 0, x, height), fill=(255, 0, 0), width=3)

        # Draw circle at touch point (bright red)
        radius = 12
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     outline=(255, 0, 0), width=4)

        # Draw coordinates with background box for visibility
        coord_text = f"Touch: ({x}, {y})"
        text_x = min(x + 15, width - 120)  # Keep text on screen
        text_y = max(y - 25, 5)

        # Draw semi-transparent background box behind text
        if font:
            bbox = draw.textbbox((text_x, text_y), coord_text, font=font)
        else:
            # Estimate bbox if no font
            bbox = (text_x, text_y, text_x + 110, text_y + 15)

        # Black background box with padding
        padding = 3
        draw.rectangle(
            (bbox[0] - padding, bbox[1] - padding,
             bbox[2] + padding, bbox[3] + padding),
            fill=(0, 0, 0)
        )

        # Draw bright yellow text on top
        if font:
            draw.text((text_x, text_y), coord_text, font=font, fill=(255, 255, 0))
        else:
            draw.text((text_x, text_y), coord_text, fill=(255, 255, 0))
