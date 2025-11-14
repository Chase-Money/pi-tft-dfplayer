"""Touch calibration screen for the v2 UI."""

from __future__ import annotations

import statistics
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget
from ..framework_v2.events import UIEvent

TARGET_OFFSETS = 40


class CalibrationScreen(ScreenView):
    name = "calibration"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.targets: List[Tuple[int, int]] = []
        self.samples: List[Tuple[int, int]] = []
        self.stage = 0
        self.message = "Tap the highlighted points"
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self._exit)

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

        self.back_button.draw(draw, fonts.get("small"))

    def _draw_target(self, draw: ImageDraw.ImageDraw, tx: int, ty: int, color: Tuple[int, int, int]) -> None:
        draw.ellipse((tx - 10, ty - 10, tx + 10, ty + 10), fill=color)
        draw.line((tx - 20, ty, tx + 20, ty), fill=color, width=2)
        draw.line((tx, ty - 20, tx, ty + 20), fill=color, width=2)

    # ------------------------------------------------------------------
    def handle_event(self, event: UIEvent) -> bool:
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
        driver_bounds = app.get_touch_driver_bounds()
        if not driver_bounds:
            app.set_status("Driver bounds unavailable", "error", 4)
            self.manager.pop()
            return

        orient = app.get_touch_orientation()
        inv_points = [self._invert_orientation(raw, orient, driver_bounds) for raw in self.samples]
        left_x = int(statistics.median([inv_points[0][0], inv_points[3][0]]))
        right_x = int(statistics.median([inv_points[1][0], inv_points[2][0]]))
        top_y = int(statistics.median([inv_points[0][1], inv_points[1][1]]))
        bottom_y = int(statistics.median([inv_points[2][1], inv_points[3][1]]))
        if right_x <= left_x:
            right_x = left_x + 1
        if bottom_y <= top_y:
            bottom_y = top_y + 1

        app.set_touch_calibration((left_x, right_x, top_y, bottom_y))
        self.manager.pop()

    def _invert_orientation(self, raw: Tuple[int, int], orient: dict, bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
        min_x, max_x, min_y, max_y = bounds
        x, y = raw
        if orient.get("SWAP_XY"):
            x, y = y, x
        if orient.get("FLIP_X"):
            x = (min_x + max_x) - x
        if orient.get("FLIP_Y"):
            y = (min_y + max_y) - y
        return x, y

    def _app(self):
        return self.services.get("app") if self.services else None

    def _exit(self):
        self.manager.pop()
