"""Home screen (v2) placeholder."""

from __future__ import annotations

from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget
from ..framework_v2.events import UIEvent


class HomeScreen(ScreenView):
    name = "home"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.buttons: List[ButtonWidget] = []

    def on_enter(self, **kwargs):
        self.buttons = [
            ButtonWidget((16, 32, 200, 60), "Browse Tracks", lambda: self.manager.push("track_browser")),
            ButtonWidget((16, 110, 200, 60), "Now Playing", lambda: self.manager.push("now_playing")),
        ]

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        font_large: ImageFont.ImageFont = context["fonts"].get("medium")
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        draw.text((16, 8), "DFPlayer", font=font_large, fill=(235, 235, 235))
        for button in self.buttons:
            button.draw(draw, font_large)

    def handle_event(self, event: UIEvent) -> bool:
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False
