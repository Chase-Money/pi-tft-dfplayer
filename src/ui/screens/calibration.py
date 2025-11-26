"""Touch calibration screen for the v2 UI."""

from __future__ import annotations

import statistics
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent

TARGET_OFFSETS = 40


class CalibrationScreen(ScreenView):
    name = "calibration"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.targets: List[Tuple[int, int]] = []
        self.samples: List[Tuple[int, int]] = []
        self.stage = 0
        self.message = "Tap the highlighted points"
        # Position back button on right side to avoid covering top-left target
        self.back_button = ButtonWidget((384, 4, 80, 40), "Back", self._exit)

    # ------------------------------------------------------------------
    def on_enter(self, **kwargs):
        app = self._app()
        width = app.framebuffer.width if app and app.framebuffer else 480
        height = app.framebuffer.height if app and app.framebuffer else 320
        # Scale offset based on screen size (40px at 480px wide, ~11px at 128px wide)
        scale = min(width / 480.0, height / 320.0)
        offset = max(10, int(TARGET_OFFSETS * scale))
        self.targets = [
            (offset, offset),
            (width - offset, offset),
            (width - offset, height - offset),
            (offset, height - offset),
        ]
        self.samples = []
        self.stage = 0
        self.message = "Tap each target (hold for a moment)"

    # ------------------------------------------------------------------
    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]

        draw.rectangle((0, 0, image.width, image.height), fill=(8, 10, 16))
        draw.text((16, 50), self.message, font=fonts.get("medium"), fill=(230, 230, 230))
        draw.text((16, 80), f"Target {min(self.stage + 1, len(self.targets))}/{len(self.targets)}", font=fonts.get("small"), fill=(200, 200, 200))

        for idx, (tx, ty) in enumerate(self.targets):
            color = (70, 90, 130)
            if idx == self.stage:
                color = (255, 215, 80)
            elif idx < self.stage:
                color = (90, 150, 90)
            self._draw_target(draw, tx, ty, color)

        # Only show back button after calibration is complete
        if self.stage >= len(self.targets):
            self.back_button.draw(draw, fonts.get("small"))

    def _draw_target(self, draw: ImageDraw.ImageDraw, tx: int, ty: int, color: Tuple[int, int, int]) -> None:
        draw.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), fill=color)
        draw.line((tx - 20, ty, tx + 20, ty), fill=color, width=2)
        draw.line((tx, ty - 20, tx, ty + 20), fill=color, width=2)

    # ------------------------------------------------------------------
    def handle_event(self, event: UIEvent) -> bool:
        # Disable back button during calibration to prevent accidental exits
        # Only enable it after calibration is complete
        if self.stage >= len(self.targets):
            if self.back_button.handle_event(event):
                return True

        if event.type != "tap":
            return False

        payload = event.payload or {}
        raw = payload.get("raw")
        pos = event.get_point()
        if raw is None or pos is None:
            self._app().set_status("Need raw touch data for calibration", "error", 4)
            return True

        if self.stage >= len(self.targets):
            return True

        self.samples.append(raw)
        self.stage += 1

        if self.stage >= len(self.targets):
            self._finalize()
        else:
            self._app().set_status(f"Captured point {self.stage}/{len(self.targets)}", "info", 2)
        return True

    # ------------------------------------------------------------------
    def _finalize(self) -> None:
        app = self._app()
        # Raw coordinates are in hardware space
        left_x = int(statistics.median([self.samples[0][0], self.samples[3][0]]))
        right_x = int(statistics.median([self.samples[1][0], self.samples[2][0]]))
        top_y = int(statistics.median([self.samples[0][1], self.samples[1][1]]))
        bottom_y = int(statistics.median([self.samples[2][1], self.samples[3][1]]))

        if right_x <= left_x:
            right_x = left_x + 1
        if bottom_y <= top_y:
            bottom_y = top_y + 1

        # Sanity checks: minimum span and within expected bounds (12-bit default)
        min_span = 20
        if (right_x - left_x) < min_span or (bottom_y - top_y) < min_span:
            app.set_status("Calibration span too small; retry", "error", 4)
            self.manager.pop()
            return
        # If driver bounds available, enforce them
        bounds = app.get_touch_driver_bounds() if hasattr(app, "get_touch_driver_bounds") else None
        if bounds:
            min_x, max_x, min_y, max_y = bounds
            span_x = max_x - min_x
            span_y = max_y - min_y
            min_required_x = max(min_span, int(0.05 * span_x))
            min_required_y = max(min_span, int(0.05 * span_y))
            if (right_x - left_x) < min_required_x or (bottom_y - top_y) < min_required_y:
                app.set_status("Calibration span too small; retry", "error", 4)
                self.manager.pop()
                return
            if not (min_x <= left_x < right_x <= max_x and min_y <= top_y < bottom_y <= max_y):
                app.set_status("Calibration out of bounds; retry", "error", 4)
                self.manager.pop()
                return

        app.set_touch_calibration(left_x, right_x, top_y, bottom_y)
        app.set_status("Calibration saved", "success", 3)
        self.manager.pop()

    def _app(self):
        return self.services.get("app") if self.services else None

    def _exit(self):
        self.manager.pop()
