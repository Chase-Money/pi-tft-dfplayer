"""Now playing screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ButtonWidget, SliderWidget
from ..framework_v2.events import UIEvent
from ..draw_utils_v2 import clamp
from ..views_v2 import (
    draw_play_indicator,
    draw_track_number,
    draw_artwork_panel,
    draw_title_line,
    draw_volume_bar,
)


class NowPlayingScreen(ScreenView):
    name = "now_playing"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.state = services.get("state") if services else None
        self.backend = services.get("backend") if services else None
        self.config = services.get("config") if services else None
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self.manager.pop)
        self.play_button = ButtonWidget((16, 250, 96, 40), self._play_label, self._toggle_play)
        self.slider = SliderWidget((16, 220, 200, 12))

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        self.back_button.draw(draw, fonts["small"])

        if not self.state:
            draw.text((16, 60), "State not available", font=fonts["medium"], fill=(255, 0, 0))
            return

        track = self.state.get_now_playing_track() or self.state.get_selected_track()
        playing = self.state.playback.playing
        volume = self.state.playback.volume
        self.slider.value = volume
        
        number = track.number if track else 0
        title = track.title if track else "No Track Selected"
        artwork = track.artwork if track else None

        draw_play_indicator(draw, playing, (16, 60), fonts["medium"])
        draw_track_number(draw, number, (60, 62), fonts["medium"])
        draw_artwork_panel(image, draw, artwork, (16, 80, 200, 120))
        draw_title_line(draw, title, (16, 200), fonts["small"], max_chars=30)
        
        self.play_button.draw(draw, fonts["small"])
        self.slider.draw(draw, fonts["small"])

    def handle_event(self, event: UIEvent) -> bool:
        if self.back_button.handle_event(event):
            return True
        if self.play_button.handle_event(event):
            return True
        
        if event.type == "tap" or event.type == "drag":
            pos = event.get_point()
            if pos and self._inside_slider(pos):
                self._set_volume_from_x(pos[0])
                return True
        return False

    def _play_label(self) -> str:
        if self.state and self.state.playback.playing:
            return "Pause"
        return "Play"

    def _toggle_play(self) -> None:
        if not self.backend or not self.state:
            return

        if self.state.playback.playing:
            self.backend.pause()
            self.state.pause_playback()
        else:
            # If a track is selected but paused, resume it.
            if self.state.get_now_playing_track() is not None:
                self.backend.resume()
                self.state.start_playback()
            # Otherwise, play the newly selected track.
            else:
                track = self.state.get_selected_track()
                if track:
                    self.backend.play_track(track.number)
                    self.state.start_playback(self.state.playback.selected_track_index)

    def _inside_slider(self, pos):
        x, y = pos
        rx, ry, rw, rh = self.slider.rect
        return rx <= x <= rx + rw and ry - 10 <= y <= ry + rh + 10

    def _set_volume_from_x(self, px):
        rx, _, rw, _ = self.slider.rect
        value = clamp(int(round((px - rx) * 30 / max(1, rw))), 0, 30)
        self.slider.value = value
        if self.state:
            self.state.set_volume(value)
        if self.backend:
            self.backend.set_volume(value)
        if self.config:
            self.config.set_volume(value)
