"""Home screen (v2) placeholder."""

from __future__ import annotations

import logging
from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent
from ..views import draw_status_banner
from ..theme_palette import get_palette
from ..framework.debug import debug_tap_logging_enabled

logger = logging.getLogger(__name__)


class HomeScreen(ScreenView):
    name = "home"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.buttons: List[ButtonWidget] = []
        self._last_resolution = None

    def on_enter(self, **kwargs):
        """Initialize screen when shown."""
        # Force button recreation on next render
        self._last_resolution = None
        self.buttons = []

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        font_large: ImageFont.ImageFont = context["fonts"].get("medium")
        w, h = image.width, image.height
        scale = context["scale"]

        palette = get_palette()
        # Clear background
        draw.rectangle((0, 0, w, h), fill=palette.bg)

        # Calculate scaled dimensions
        margin = max(4, int(16 * scale))
        title_y = max(4, int(12 * scale))
        button_height = max(20, int(60 * scale))
        button_width = int(w * 0.85)  # 85% of screen width
        button_spacing = max(8, int(18 * scale))

        # Starting Y position for buttons (below title)
        start_y = title_y + int(40 * scale)

        # Only recreate buttons if resolution changed (optimization while preventing state leakage)
        current_res = (w, h)
        if current_res != self._last_resolution:
            dbg = debug_tap_logging_enabled()
            # Note: Home screen has no back button since it's the root screen
            self.buttons = [
                ButtonWidget(
                    (margin, start_y, button_width, button_height),
                    "Browse Tracks",
                    lambda: self.manager.push("track_browser"),
                    debug_log=dbg,
                ),
                ButtonWidget(
                    (margin, start_y + button_height + button_spacing, button_width, button_height),
                    "Now Playing",
                    lambda: self.manager.push("now_playing"),
                    debug_log=dbg,
                ),
                ButtonWidget(
                    (margin, start_y + 2 * (button_height + button_spacing), button_width, button_height),
                    "Settings",
                    lambda: self.manager.push("settings"),
                    debug_log=dbg,
                ),
            ]
            self._last_resolution = current_res

        # Draw title
        draw.text((margin, title_y), "DFPlayer", font=font_large, fill=palette.text)

        # Draw buttons
        for button in self.buttons:
            button.draw(draw, font_large)
        # Track dirty rect for potential partial present
        self.last_dirty = [(margin, start_y, button_width, 3 * button_height + 2 * button_spacing)]

    def handle_event(self, event: UIEvent) -> bool:
        # Extract coordinates from event payload
        pos = event.payload.get("pos") if event.payload else None
        x, y = pos if pos else (None, None)

        # CRITICAL FIX: Clear all button pressed states on new press to prevent state leak
        if event.type == "press":
            for button in self.buttons:
                button._pressed = False

        if event.type == "tap" and pos:
            logger.info(f"[HOME] Processing tap at ({x}, {y})")
            for i, button in enumerate(self.buttons):
                rx, ry, rw, rh = button.rect
                label_text = button.label if isinstance(button.label, str) else button.label()
                logger.info(f"[HOME]   Button {i} '{label_text}': rect=({rx}, {ry}, {rw}, {rh}) → x:[{rx}-{rx+rw}] y:[{ry}-{ry+rh}]")

        for i, button in enumerate(self.buttons):
            if button.handle_event(event):
                # Only log successful button presses
                label_text = button.label if isinstance(button.label, str) else button.label()
                logger.info(f"[HOME] Button '{label_text}' pressed")
                return True

        return False

    def _app(self):
        return self.services.get("app") if self.services else None
