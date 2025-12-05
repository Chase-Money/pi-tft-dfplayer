"""Touch diagnostic screen for hardware coordinate mapping."""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent

logger = logging.getLogger(__name__)


class TouchDiagnosticScreen(ScreenView):
    """
    Diagnostic screen for mapping touch digitizer coordinate system.

    Displays corner targets and logs raw hardware coordinates across
    tap/press/drag events to help determine correct orientation and
    calibration mapping.
    """

    name = "touch_diagnostic"
    HISTORY_LIMIT = 10

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.back_button = None
        self.tap_history: List[Tuple[str, int, int, int, int, str]] = []
        self.last_tap: Optional[Tuple[int, int, int, int, str, str]] = None
        self.driver_bounds: Optional[Tuple[int, int, int, int]] = None
        self.orientation: Optional[dict] = None

    def on_enter(self, **kwargs):
        """Reset tap history when entering screen."""
        self.tap_history = []
        self.last_tap = None

        app = self._app()
        if app:
            self.orientation = app.get_touch_orientation()
            self.driver_bounds = app.get_touch_driver_bounds()
            logger.info("Touch orientation: %s", self.orientation)
            logger.info("Driver bounds: %s", self.driver_bounds)

        logger.info("=" * 80)
        logger.info("TOUCH DIAGNOSTIC MODE - Tap each corner and watch the logs")
        logger.info("=" * 80)

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        w, h = image.width, image.height
        scale = context["scale"]

        # Clear background
        draw.rectangle((0, 0, w, h), fill=(20, 20, 40))

        # Calculate margins for corner targets
        margin = max(10, int(40 * scale))
        target_size = max(40, int(80 * scale))

        # Define corner positions (display coordinates)
        corners = [
            ("TOP-LEFT", margin, margin),
            ("TOP-RIGHT", w - margin - target_size, margin),
            ("BOTTOM-RIGHT", w - margin - target_size, h - margin - target_size),
            ("BOTTOM-LEFT", margin, h - margin - target_size),
        ]

        # Draw corner targets
        for label, x, y in corners:
            # Draw target box
            draw.rectangle(
                (x, y, x + target_size, y + target_size),
                fill=(100, 100, 200),
                outline=(200, 200, 255),
                width=2
            )

            # Draw label
            font = fonts.get("small")
            # Split label for better fit
            parts = label.split("-")
            for i, part in enumerate(parts):
                bbox = draw.textbbox((0, 0), part, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                text_x = x + (target_size - text_w) // 2
                text_y = y + (target_size - (len(parts) * text_h + 4)) // 2 + i * (text_h + 4)
                draw.text((text_x, text_y), part, font=font, fill=(255, 255, 255))

        # Draw instructions
        title = "Touch Diagnostic - Tap Each Corner"
        font_large = fonts.get("medium")
        bbox = draw.textbbox((0, 0), title, font=font_large)
        title_w = bbox[2] - bbox[0]
        draw.text(((w - title_w) // 2, 10), title, font=font_large, fill=(255, 255, 100))

        status_y = 40 + font_large.size
        status_lines = []
        if self.orientation:
            status_lines.append(f"Orientation: {self.orientation}")
        if self.driver_bounds:
            min_x, max_x, min_y, max_y = self.driver_bounds
            status_lines.append(f"Driver bounds: x[{min_x},{max_x}] y[{min_y},{max_y}]")
        status_lines.append(f"Events logged: {len(self.tap_history)}")

        for i, line in enumerate(status_lines):
            draw.text((16, status_y + i * 18), line, font=fonts.get("small"), fill=(200, 220, 255))

        history_start = status_y + len(status_lines) * 18 + 10
        recent_events = list(reversed(self.tap_history[-5:]))
        for idx, entry in enumerate(recent_events):
            label, raw_x, raw_y, screen_x, screen_y, event_type = entry
            text = f"{event_type[:6]} {label}: raw({raw_x},{raw_y}) scr({screen_x},{screen_y})"
            draw.text((16, history_start + idx * 18), text, font=fonts.get("small"), fill=(180, 200, 230))

        # Show last tap info on screen
        if self.last_tap:
            raw_x, raw_y, screen_x, screen_y, event_type, label = self.last_tap
            info_y = h // 2 - 60
            font_info = fonts.get("small")

            info_lines = [
                "Last Event:",
                f"Type:   {event_type} ({label})",
                f"Raw:    ({raw_x}, {raw_y})",
                f"Screen: ({screen_x}, {screen_y})",
                "",
                "Check logs for details",
            ]

            for i, line in enumerate(info_lines):
                draw.text((w // 2 - 110, info_y + i * 18), line,
                         font=font_info, fill=(255, 255, 255))

        # Draw back button (top right)
        if not self.back_button:
            back_w = max(30, int(80 * scale))
            button_h = max(16, int(40 * scale))
            margin_btn = max(4, int(16 * scale))
            small_margin = max(2, int(4 * scale))
            back_x = w - margin_btn - back_w
            self.back_button = ButtonWidget(
                (back_x, small_margin, back_w, button_h),
                "Back",
                self._go_back,
            )

        self.back_button.draw(draw, fonts.get("small"))

    def _go_back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: UIEvent) -> bool:
        """Handle touch events and log raw coordinates."""
        if self.back_button and self.back_button.handle_event(event):
            return True

        payload = event.payload or {}
        raw = payload.get("raw")
        pos = event.get_point()

        if raw and pos and event.type in {"tap", "press", "drag", "release", "swipe"}:
            raw_x, raw_y = raw
            screen_x, screen_y = pos
            label = self._identify_corner(screen_x, screen_y)
            self._record_event(event.type, label, raw_x, raw_y, screen_x, screen_y)
            return True

        return False

    def _record_event(
        self,
        event_type: str,
        label: str,
        raw_x: int,
        raw_y: int,
        screen_x: int,
        screen_y: int,
    ) -> None:
        """Record an event with raw + screen coordinates and log details."""
        self.tap_history.append((label, raw_x, raw_y, screen_x, screen_y, event_type))
        if len(self.tap_history) > self.HISTORY_LIMIT:
            self.tap_history.pop(0)

        self.last_tap = (raw_x, raw_y, screen_x, screen_y, event_type, label)

        logger.info("-" * 80)
        logger.info("%s #%d: %s", event_type.upper(), len(self.tap_history), label)
        logger.info("  Raw coordinates:    (%4d, %4d)", raw_x, raw_y)
        logger.info("  Screen coordinates: (%3d, %3d)", screen_x, screen_y)
        if self.driver_bounds:
            min_x, max_x, min_y, max_y = self.driver_bounds
            logger.info("  Driver bounds: x[%d,%d] y[%d,%d]", min_x, max_x, min_y, max_y)
        if self.orientation:
            logger.info("  Orientation: %s", self.orientation)
        logger.info("-" * 80)

    def _identify_corner(self, x: int, y: int) -> str:
        """Identify which corner was tapped based on screen coordinates."""
        app = self._app()
        if not app:
            return "UNKNOWN"

        w = app.framebuffer.width if app.framebuffer else 480
        h = app.framebuffer.height if app.framebuffer else 320

        mid_x = w // 2
        mid_y = h // 2

        if x < mid_x and y < mid_y:
            return "TOP-LEFT"
        elif x >= mid_x and y < mid_y:
            return "TOP-RIGHT"
        elif x >= mid_x and y >= mid_y:
            return "BOTTOM-RIGHT"
        else:
            return "BOTTOM-LEFT"

    def _app(self):
        """Get app instance from services."""
        return self.services.get("app") if self.services else None
