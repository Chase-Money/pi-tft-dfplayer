"""Settings screen with orientation + calibration shortcuts."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget
from ..framework_v2.events import UIEvent
from ..views_v2 import draw_status_banner


class SettingsScreen(ScreenView):
    name = "settings"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        # Widgets created dynamically in render based on resolution
        self.orientation_button = None
        self.cal_button = None
        self.back_button = None
        self._orientation_idx = 0

    def on_enter(self, **kwargs):
        app = self._app()
        if app:
            self._orientation_idx = app.orientation_index

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        w, h = image.width, image.height
        scale = context["scale"]

        # Clear background
        draw.rectangle((0, 0, w, h), fill=(12, 16, 24))

        # Calculate scaled dimensions
        margin = max(4, int(16 * scale))
        small_margin = max(2, int(4 * scale))
        button_h = max(20, int(60 * scale))
        back_w = max(30, int(80 * scale))
        button_w = int(w * 0.75)  # 75% of screen width
        title_y = max(16, int(50 * scale))
        orient_y = max(32, int(80 * scale))
        cal_y = orient_y + button_h + max(12, int(20 * scale))
        label_offset = max(8, int(20 * scale))

        # Create widgets dynamically
        self.back_button = ButtonWidget((margin, small_margin, back_w, max(16, int(40 * scale))), "Back", self.manager.pop)
        self.orientation_button = ButtonWidget((margin, orient_y, button_w, button_h), self._orientation_label, self._cycle_orientation)
        self.cal_button = ButtonWidget((margin, cal_y, button_w, button_h), "Calibrate Touch", self._open_calibration)

        # Draw status banner
        app = self._app()
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], w, fonts, status[1])

        # Draw title and labels
        draw.text((margin, title_y), "Settings", font=fonts.get("medium"), fill=(235, 235, 235))
        draw.text((margin, orient_y - label_offset), "Touch Orientation", font=fonts.get("small"), fill=(200, 200, 200))
        draw.text((margin, cal_y - label_offset), "Calibration", font=fonts.get("small"), fill=(200, 200, 200))

        # Draw widgets
        self.back_button.draw(draw, fonts.get("small"))
        self.orientation_button.draw(draw, fonts.get("small"))
        self.cal_button.draw(draw, fonts.get("small"))

    def handle_event(self, event: UIEvent) -> bool:
        if self.back_button.handle_event(event):
            return True
        if self.orientation_button.handle_event(event):
            return True
        if self.cal_button.handle_event(event):
            return True
        return False

    # ------------------------------------------------------------------
    def _orientation_label(self) -> str:
        return f"Orientation {self._orientation_idx + 1}/8"

    def _cycle_orientation(self) -> None:
        app = self._app()
        if not app:
            return
        self._orientation_idx = (self._orientation_idx + 1) % 8
        app.set_touch_orientation(self._orientation_idx)

    def _open_calibration(self) -> None:
        self.manager.push("calibration")

    def _app(self):
        return self.services.get("app") if self.services else None
