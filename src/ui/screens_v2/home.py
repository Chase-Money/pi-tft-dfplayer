"""Home screen (v2) placeholder."""

from __future__ import annotations

import logging
from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget
from ..framework_v2.events import UIEvent
from ..views_v2 import draw_status_banner

logger = logging.getLogger(__name__)


class HomeScreen(ScreenView):
    name = "home"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.buttons: List[ButtonWidget] = []

    def on_enter(self, **kwargs):
        """Initialize screen - create buttons once based on current resolution."""
        # Get screen dimensions from context (will be set by first render if not available)
        self.buttons = []
        self._buttons_created = False

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        font_large: ImageFont.ImageFont = context["fonts"].get("medium")
        w, h = image.width, image.height
        scale = context["scale"]

        # Clear background
        draw.rectangle((0, 0, w, h), fill=(12, 16, 24))

        # Calculate scaled dimensions
        margin = max(4, int(16 * scale))
        title_y = max(4, int(12 * scale))
        button_height = max(20, int(60 * scale))
        button_width = int(w * 0.85)  # 85% of screen width
        button_spacing = max(8, int(18 * scale))

        # Starting Y position for buttons (below title)
        start_y = title_y + int(40 * scale)

        # Create buttons only once (on first render)
        if not self._buttons_created:
            self.buttons = [
                ButtonWidget(
                    (margin, start_y, button_width, button_height),
                    "Browse Tracks",
                    lambda: self.manager.push("track_browser")
                ),
                ButtonWidget(
                    (margin, start_y + button_height + button_spacing, button_width, button_height),
                    "Now Playing",
                    lambda: self.manager.push("now_playing")
                ),
                ButtonWidget(
                    (margin, start_y + 2 * (button_height + button_spacing), button_width, button_height),
                    "Settings",
                    lambda: self.manager.push("settings")
                ),
            ]
            self._buttons_created = True

        # Draw status banner if present
        app = self._app()
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], w, context["fonts"], status[1])

        # Draw title
        draw.text((margin, title_y), "DFPlayer", font=font_large, fill=(235, 235, 235))

        # Draw buttons
        for button in self.buttons:
            button.draw(draw, font_large)

    def handle_event(self, event: UIEvent) -> bool:
        # Extract coordinates from event payload
        pos = event.payload.get("pos") if event.payload else None
        x, y = pos if pos else (None, None)

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
