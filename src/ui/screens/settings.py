"""Settings screen with orientation + calibration shortcuts."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget
from ..framework.events import UIEvent
from ..views import draw_status_banner


class SettingsScreen(ScreenView):
    name = "settings"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.orientation_button = None
        self.cal_button = None
        self.back_button = None
        self._orientation_idx = 0
        self._last_resolution = None

    def on_enter(self, **kwargs):
        self._orientation_idx = 0  # Stub: orientation not yet implemented in v2
        self._last_resolution = None

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        w, h = image.width, image.height
        scale = context["scale"]

        # Clear background
        draw.rectangle((0, 0, w, h), fill=(12, 16, 24))

        # Only recreate widgets if resolution changed
        current_res = (w, h)
        if current_res != self._last_resolution:
            margin = max(4, int(16 * scale))
            small_margin = max(2, int(4 * scale))
            button_h = max(20, int(60 * scale))
            back_w = max(30, int(80 * scale))
            button_w = int(w * 0.75)
            title_y = max(16, int(50 * scale))
            orient_y = max(32, int(80 * scale))
            cal_y = orient_y + button_h + max(12, int(20 * scale))

            self.back_button = ButtonWidget((margin, small_margin, back_w, max(16, int(40 * scale))), "Back", self.manager.pop)
            self.orientation_button = ButtonWidget((margin, orient_y, button_w, button_h), self._orientation_label, self._cycle_orientation)
            self.cal_button = ButtonWidget((margin, cal_y, button_w, button_h), "Calibrate Touch", self._open_calibration)
            self._last_resolution = current_res

        # Draw status banner
        app = self._app()
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], w, fonts, status[1])

        # Draw title and labels
        margin = max(4, int(16 * scale))
        title_y = max(16, int(50 * scale))
        orient_y = max(32, int(80 * scale))
        button_h = max(20, int(60 * scale))
        cal_y = orient_y + button_h + max(12, int(20 * scale))
        label_offset = max(8, int(20 * scale))

        draw.text((margin, title_y), "Settings", font=fonts.get("medium"), fill=(235, 235, 235))
        draw.text((margin, orient_y - label_offset), "Touch Orientation", font=fonts.get("small"), fill=(200, 200, 200))
        draw.text((margin, cal_y - label_offset), "Calibration", font=fonts.get("small"), fill=(200, 200, 200))

        # Draw widgets
        if self.back_button:
            self.back_button.draw(draw, fonts.get("small"))
        if self.orientation_button:
            self.orientation_button.draw(draw, fonts.get("small"))
        if self.cal_button:
            self.cal_button.draw(draw, fonts.get("small"))

    def handle_event(self, event: UIEvent) -> bool:
        if self.back_button and self.back_button.handle_event(event):
            return True
        if self.orientation_button and self.orientation_button.handle_event(event):
            return True
        if self.cal_button and self.cal_button.handle_event(event):
            return True
        return False

    def _orientation_label(self) -> str:
        return f"Orientation {self._orientation_idx + 1}/8"

    def _cycle_orientation(self) -> None:
        # Stub: Touch orientation not yet implemented in v2 app
        self._orientation_idx = (self._orientation_idx + 1) % 8
        # TODO: Implement touch orientation in app_v2.py

    def _open_calibration(self) -> None:
        self.manager.push("calibration")

    def _app(self):
        return self.services.get("app") if self.services else None
