"""Track browser screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ListWidget, ButtonWidget
from ..framework_v2.events import UIEvent


class TrackBrowserScreen(ScreenView):
    name = "track_browser"

    def __init__(self, manager):
        super().__init__(manager)
        self.list_widget = ListWidget(["Track 001", "Track 002", "Track 003"], visible_rows=4)
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self.manager.pop)

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        draw.text((110, 12), "Tracks", font=fonts["medium"], fill=(235, 235, 235))
        self.back_button.draw(draw, fonts["small"])
        self.list_widget.draw(draw, (16, 60, image.width - 32, image.height - 80), fonts["small"])

    def handle_event(self, event: UIEvent) -> bool:
        if event.type == "swipe":
            delta = event.payload.get("delta", 0)
            self.list_widget.move_selection(delta)
            return True
        if self.back_button.handle_event(event):
            return True
        if event.type == "tap":
            # Future: select track based on tap row
            return True
        return False

