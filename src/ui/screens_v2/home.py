"""Home screen (v2) placeholder."""

from __future__ import annotations

from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget
from ..framework_v2.events import UIEvent
from ..views_v2 import draw_status_banner


class HomeScreen(ScreenView):
    name = "home"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.buttons: List[ButtonWidget] = []

    def on_enter(self, **kwargs):
        self.buttons = [
            ButtonWidget((16, 64, 200, 60), "Browse Tracks", lambda: self.manager.push("track_browser")),
            ButtonWidget((16, 142, 200, 60), "Now Playing", lambda: self.manager.push("now_playing")),
            ButtonWidget((16, 220, 200, 60), "Settings", lambda: self.manager.push("settings")),
        ]

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        font_large: ImageFont.ImageFont = context["fonts"].get("medium")
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        app = self._app()
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], image.width, context["fonts"], status[1])
        draw.text((16, 12), "DFPlayer", font=font_large, fill=(235, 235, 235))
        for button in self.buttons:
            button.draw(draw, font_large)

    def handle_event(self, event: UIEvent) -> bool:
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False

    def _app(self):
        return self.services.get("app") if self.services else None
