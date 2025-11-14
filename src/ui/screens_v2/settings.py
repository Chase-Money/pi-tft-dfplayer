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
        self.orientation_button = ButtonWidget((16, 80, 200, 60), self._orientation_label, self._cycle_orientation)
        self.cal_button = ButtonWidget((16, 160, 200, 60), "Calibrate Touch", self._open_calibration)
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self.manager.pop)
        self._orientation_idx = 0

    def on_enter(self, **kwargs):
        app = self._app()
        if app:
            self._orientation_idx = app.orientation_index

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        app = self._app()
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], image.width, fonts, status[1])
        draw.text((16, 50), "Settings", font=fonts.get("medium"), fill=(235, 235, 235))
        draw.text((16, 120), "Touch Orientation", font=fonts.get("small"), fill=(200, 200, 200))
        draw.text((16, 200), "Calibration", font=fonts.get("small"), fill=(200, 200, 200))
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
