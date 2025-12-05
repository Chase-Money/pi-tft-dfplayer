"""Touch calibration screen for the v2 UI."""

from __future__ import annotations

import statistics
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent

# Calibration constants - chosen through empirical testing on 3.5" touchscreens
# These values balance accuracy, UX speed, and visibility on small displays
TARGET_OFFSETS = 40  # Distance from screen edges (px) - scales with resolution in on_enter()
SAMPLES_PER_TARGET = 3  # Samples per corner - provides median filtering without excessive taps
TARGET_RADIUS = 18  # Target circle size (px) - visible on small screens, not too intrusive


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
        # Back button will be created in render() based on resolution
        self.back_button = None
        # Save original orientation to restore after calibration
        self.saved_orientation = None

    # ------------------------------------------------------------------
    def on_enter(self, **kwargs):
        import logging
        logger = logging.getLogger(__name__)

        app = self._app()
        width = app.framebuffer.width if app and app.framebuffer else 480
        height = app.framebuffer.height if app and app.framebuffer else 320

        # Save current orientation and calibration, disable both during calibration
        # This ensures raw coordinate collection works correctly regardless of digitizer rotation
        if app and hasattr(app, 'get_touch_orientation'):
            self.saved_orientation = app.get_touch_orientation()
            logger.info(f"Saved orientation for calibration: {self.saved_orientation}")

            # Disable orientation transform (identity) and reset calibration to hardware bounds
            # This provides clean raw coordinates for accurate calibration
            if hasattr(app, 'touch_controller') and app.touch_controller:
                # Disable all orientation transforms
                app.touch_controller.set_orientation(swap_xy=False, flip_x=False, flip_y=False)
                logger.info("Disabled orientation transform for calibration")

                # Reset calibration to hardware driver bounds for 1:1 raw coordinate mapping
                driver_bounds = app.get_touch_driver_bounds()
                if driver_bounds:
                    min_x, max_x, min_y, max_y = driver_bounds
                    logger.info(f"Temporarily resetting calibration to driver bounds: ({min_x}, {max_x}, {min_y}, {max_y})")
                    app.touch_controller.set_calibration(min_x, max_x, min_y, max_y)
                    app.set_status("Tap the target circles (ignore position)", "info", 3)
                else:
                    logger.warning("Could not get driver bounds, using existing calibration")
                    app.set_status("Starting calibration", "info", 2)

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
        w, h = image.width, image.height

        # Create back button positioned on right side (only shown after calibration completes)
        if not self.back_button:
            back_w = max(30, int(80 * (min(w / 480.0, h / 320.0))))
            button_h = max(16, int(40 * (min(w / 480.0, h / 320.0))))
            margin = max(4, int(16 * (min(w / 480.0, h / 320.0))))
            small_margin = max(2, int(4 * (min(w / 480.0, h / 320.0))))
            back_x = w - margin - back_w
            self.back_button = ButtonWidget((back_x, small_margin, back_w, button_h), "Back", self._exit)

        draw.rectangle((0, 0, w, h), fill=(8, 10, 16))

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
        # Get hardware bounds for validation
        bounds = app.get_touch_driver_bounds() if hasattr(app, "get_touch_driver_bounds") else None
        NOISE_THRESHOLD = 50  # Filter samples near hardware minimum (spurious readings)

        # Compute median of each target's samples, filtering invalid ones
        median_samples = []
        for target_samples in self.samples:
            if not target_samples:
                continue

            # Filter out samples near hardware minimum bounds (noise)
            valid_samples = []
            for raw_x, raw_y in target_samples:
                if bounds:
                    min_x, max_x, min_y, max_y = bounds
                    # Reject samples too close to hardware minimum (spurious readings)
                    if raw_x <= min_x + NOISE_THRESHOLD or raw_y <= min_y + NOISE_THRESHOLD:
                        continue
                    # Reject samples outside hardware bounds
                    if not (min_x <= raw_x <= max_x and min_y <= raw_y <= max_y):
                        continue
                valid_samples.append((raw_x, raw_y))

            # Need at least half the samples to be valid
            if len(valid_samples) < len(target_samples) // 2:
                app.set_status("Too many invalid samples; retry calibration", "error", 4)
                self._restore_orientation()
                self.manager.pop()
                return

            # Use valid samples (or all if no bounds check)
            samples_to_use = valid_samples if valid_samples else target_samples
            med_x = int(statistics.median([s[0] for s in samples_to_use]))
            med_y = int(statistics.median([s[1] for s in samples_to_use]))
            median_samples.append((med_x, med_y))

        if len(median_samples) != 4:
            app.set_status("Calibration failed: missing samples", "error", 4)
            self._restore_orientation()
            self.manager.pop()
            return

        # Compute calibration bounds using min/max across ALL samples
        # This works regardless of how the touch digitizer is physically mounted
        # relative to the display (no assumptions about corner mapping)
        all_x = [s[0] for s in median_samples]
        all_y = [s[1] for s in median_samples]
        left_x = min(all_x)
        right_x = max(all_x)
        top_y = min(all_y)
        bottom_y = max(all_y)

        if right_x <= left_x:
            right_x = left_x + 1
        if bottom_y <= top_y:
            bottom_y = top_y + 1

        # Sanity checks: minimum span and within expected bounds (12-bit default)
        # TEMPORARY: If span is extremely small (< 20px), likely orientation is wrong
        # Save the calibration anyway and warn user to fix orientation first
        min_span = 20
        actual_span_x = right_x - left_x
        actual_span_y = bottom_y - top_y

        if actual_span_x < min_span or actual_span_y < min_span:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Calibration span too small: X={actual_span_x} Y={actual_span_y} (min={min_span})")
            logger.error(f"  Bounds: left={left_x} right={right_x} top={top_y} bottom={bottom_y}")
            logger.error(f"  Raw samples: {median_samples}")
            logger.error(f"  Hardware issue or not tapping corners correctly!")
            app.set_status("Calibration failed: tap the corners accurately", "error", 5)
            self._restore_orientation()
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

            if actual_span_x < min_required_x or actual_span_y < min_required_y:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Calibration span below 5% threshold:")
                logger.error(f"  Actual: X={actual_span_x} Y={actual_span_y}")
                logger.error(f"  Required: X={min_required_x} Y={min_required_y} (5% of {span_x}x{span_y})")
                logger.error(f"  Raw samples: {median_samples}")
                app.set_status(f"Need {min_required_x}x{min_required_y}, got {actual_span_x}x{actual_span_y}", "error", 5)
                self._restore_orientation()
                self.manager.pop()
                return
            if not (min_x <= left_x < right_x <= max_x and min_y <= top_y < bottom_y <= max_y):
                app.set_status("Calibration out of bounds; retry", "error", 4)
                self._restore_orientation()
                self.manager.pop()
                return

        # Final sanity to avoid inverted coordinates
        if left_x >= right_x or top_y >= bottom_y:
            app.set_status("Invalid calibration: please retry", "error", 4)
            self._restore_orientation()
            self.manager.pop()
            return

        app.set_touch_calibration((left_x, right_x, top_y, bottom_y))
        app.set_status("Calibration saved", "success", 3)

        # Restore original orientation
        self._restore_orientation()

        self.manager.pop()

    def _restore_orientation(self) -> None:
        """Restore orientation settings after calibration completes."""
        import logging
        logger = logging.getLogger(__name__)

        app = self._app()
        if not app or not self.saved_orientation:
            return

        # Restore the orientation that was active before calibration
        if hasattr(app, 'touch_controller') and app.touch_controller:
            app.touch_controller.set_orientation(
                swap_xy=self.saved_orientation.get('swap_xy', False),
                flip_x=self.saved_orientation.get('flip_x', False),
                flip_y=self.saved_orientation.get('flip_y', False)
            )
            logger.info(f"Restored orientation after calibration: {self.saved_orientation}")
            app.set_status("Calibration saved", "success", 2)

    def _app(self):
        return self.services.get("app") if self.services else None

    def _exit(self):
        # Restore orientation before exiting
        self._restore_orientation()
        self.manager.pop()
