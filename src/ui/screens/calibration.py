"""Touch calibration screen for the v2 UI."""

from __future__ import annotations

import statistics
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent

TARGET_OFFSETS = 40
SAMPLES_PER_TARGET = 3  # Collect multiple samples per target for median filtering
TARGET_RADIUS = 18  # Larger targets for easier tapping


class CalibrationScreen(ScreenView):
    name = "calibration"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.targets: List[Tuple[int, int]] = []
        self.samples: List[List[Tuple[int, int]]] = []  # List of sample lists, one per target
        self.stage = 0
        self.sample_count = 0  # Samples collected for current target
        self.message = "Tap the highlighted points"
        self.flash_until = 0.0  # For visual feedback on tap
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
        self.samples = [[] for _ in self.targets]  # List of sample lists
        self.stage = 0
        self.sample_count = 0
        self.message = f"Tap each target {SAMPLES_PER_TARGET} times"

    # ------------------------------------------------------------------
    def render(self, context: dict) -> None:
        import time
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]

        draw.rectangle((0, 0, image.width, image.height), fill=(8, 10, 16))

        # Instructions
        draw.text((16, 50), self.message, font=fonts.get("medium"), fill=(230, 230, 230))

        # Progress indicator
        if self.stage < len(self.targets):
            progress_text = f"Target {self.stage + 1}/{len(self.targets)} - Sample {self.sample_count}/{SAMPLES_PER_TARGET}"
            draw.text((16, 80), progress_text, font=fonts.get("small"), fill=(200, 200, 200))
        else:
            draw.text((16, 80), "Calibration complete!", font=fonts.get("small"), fill=(90, 230, 90))

        # Draw all targets
        for idx, (tx, ty) in enumerate(self.targets):
            color = (70, 90, 130)  # Inactive
            if idx == self.stage:
                color = (255, 215, 80)  # Active (yellow/gold)
            elif idx < self.stage:
                color = (90, 180, 90)  # Completed (green)

            # Flash effect when sample collected
            if idx == self.stage and time.monotonic() < self.flash_until:
                color = (255, 255, 255)  # White flash

            self._draw_target(draw, tx, ty, color, active=(idx == self.stage))

        # Only show back button after calibration is complete
        if self.stage >= len(self.targets):
            self.back_button.draw(draw, fonts.get("small"))

    def _draw_target(self, draw: ImageDraw.ImageDraw, tx: int, ty: int, color: Tuple[int, int, int], active: bool = False) -> None:
        radius = TARGET_RADIUS

        # Draw outer ring for active target
        if active:
            draw.ellipse((tx - radius - 4, ty - radius - 4, tx + radius + 4, ty + radius + 4),
                        outline=color, width=3)

        # Draw main target circle
        draw.ellipse((tx - radius, ty - radius, tx + radius, ty + radius), fill=color)

        # Draw crosshairs
        crosshair_len = radius + 8
        draw.line((tx - crosshair_len, ty, tx + crosshair_len, ty), fill=color, width=3)
        draw.line((tx, ty - crosshair_len, tx, ty + crosshair_len), fill=color, width=3)

        # Draw center dot
        draw.ellipse((tx - 3, ty - 3, tx + 3, ty + 3), fill=(255, 255, 255) if active else (200, 200, 200))

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

        # Collect multiple samples per target for median filtering
        self.samples[self.stage].append(raw)
        self.sample_count += 1

        # Flash effect for visual feedback
        import time
        self.flash_until = time.monotonic() + 0.2

        if self.sample_count >= SAMPLES_PER_TARGET:
            # Move to next target
            self.stage += 1
            self.sample_count = 0

            if self.stage >= len(self.targets):
                self._finalize()
            else:
                self._app().set_status(f"Target {self.stage + 1}/{len(self.targets)}", "info", 2)
        else:
            # Need more samples for current target
            self._app().set_status(f"Sample {self.sample_count}/{SAMPLES_PER_TARGET} collected", "info", 1)
        return True

    # ------------------------------------------------------------------
    def _finalize(self) -> None:
        app = self._app()
        # Compute median of each target's samples
        median_samples = []
        for target_samples in self.samples:
            if not target_samples:
                continue
            med_x = int(statistics.median([s[0] for s in target_samples]))
            med_y = int(statistics.median([s[1] for s in target_samples]))
            median_samples.append((med_x, med_y))

        # Now compute calibration bounds from median samples (same as before)
        left_x = int(statistics.median([median_samples[0][0], median_samples[3][0]]))
        right_x = int(statistics.median([median_samples[1][0], median_samples[2][0]]))
        top_y = int(statistics.median([median_samples[0][1], median_samples[1][1]]))
        bottom_y = int(statistics.median([median_samples[2][1], median_samples[3][1]]))

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
