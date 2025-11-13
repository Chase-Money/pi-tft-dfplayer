"""Now playing screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget, SliderWidget
from ..framework_v2.events import UIEvent
from ..views_v2 import (
    draw_play_indicator,
    draw_track_number,
    draw_artwork_panel,
    draw_title_line,
    draw_volume_bar,
)


class NowPlayingScreen(ScreenView):
    name = "now_playing"

    def __init__(self, manager):
        super().__init__(manager)
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self.manager.pop)
        self.play_button = ButtonWidget((16, 180, 96, 40), "Play/Pause", lambda: None)
        self.slider = SliderWidget((16, 140, 200, 12))

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        state = context.get("state")

        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        self.back_button.draw(draw, fonts["small"])

        playing = getattr(state, "playing", False)
        number = getattr(state, "track_number", 0)
        title = getattr(state, "title", "No Track")
        artwork = getattr(state, "artwork_path", None)
        volume = getattr(state, "volume", self.slider.value)
        self.slider.value = volume

        draw_play_indicator(draw, playing, (16, 60), fonts["medium"])
        draw_track_number(draw, number, (60, 62), fonts["medium"])
        draw_artwork_panel(image, draw, artwork, (16, 80, 96, 96))
        draw_title_line(draw, title, (16, 190), fonts["small"], max_chars=20)
        draw_volume_bar(draw, volume, (16, 210, 200, 10))
        self.play_button.draw(draw, fonts["small"])

    def handle_event(self, event: UIEvent) -> bool:
        if self.back_button.handle_event(event):
            return True
        if self.play_button.handle_event(event):
            return True
        if self.slider.handle_event(event):
            return True
        return False

