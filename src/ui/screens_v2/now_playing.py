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
    draw_status_banner,
)


class NowPlayingScreen(ScreenView):
    name = "now_playing"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.state = services.get("state") if services else None
        self.backend = services.get("backend") if services else None
        self.config = services.get("config") if services else None
        # Widgets will be created dynamically in render based on resolution
        self.back_button = None
        self.play_button = None
        self.slider = None
        self._last_resolution = None

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
        button_h = max(16, int(40 * scale))
        back_w = max(30, int(80 * scale))
        play_w = max(40, int(96 * scale))
        slider_h = max(8, int(12 * scale))

        # Layout calculations (percentage-based for flexibility)
        info_y = max(24, int(60 * scale))
        artwork_y = info_y + max(16, int(20 * scale))
        artwork_size = min(int(w * 0.6), int(h * 0.4), max(60, int(120 * scale)))
        title_y = artwork_y + artwork_size + max(4, int(8 * scale))
        slider_y = title_y + max(12, int(20 * scale))
        button_y = slider_y + slider_h + max(8, int(12 * scale))

        # Create widgets dynamically based on resolution
        self.back_button = ButtonWidget((margin, small_margin, back_w, button_h), "Back", self.manager.pop)
        self.play_button = ButtonWidget((margin, button_y, play_w, button_h), self._play_label, self._toggle_play)
        self.slider = SliderWidget((margin, slider_y, int(w * 0.7), slider_h))

        # Draw status banner
        app = self.services.get("app") if self.services else None
        if app:
            status = app.get_status()
            if status:
                draw_status_banner(draw, status[0], w, fonts, status[1])

        # Draw back button
        self.back_button.draw(draw, fonts["small"])

        if not self.state:
            draw.text((margin, info_y), "State not available", font=fonts["medium"], fill=(255, 0, 0))
            return

        track = self.state.get_now_playing_track() or self.state.get_selected_track()
        playing = self.state.playback.playing
        volume = self.state.playback.volume
        self.slider.value = volume

        number = track.number if track else 0
        title = track.title if track else "No Track Selected"
        artwork = track.artwork if track else None

        # Draw playback info
        draw_play_indicator(draw, playing, (margin, info_y), fonts["medium"])
        track_num_x = margin + max(20, int(44 * scale))
        draw_track_number(draw, number, (track_num_x, info_y + max(1, int(2 * scale))), fonts["medium"])

        # Draw artwork or placeholder
        if artwork:
            draw_artwork_panel(image, draw, artwork, (margin, artwork_y, artwork_size, artwork_size))
        else:
            draw.rectangle(
                (margin, artwork_y, margin + artwork_size, artwork_y + artwork_size),
                outline=(80, 80, 90),
                width=max(1, int(2 * scale))
            )
            no_art_y = artwork_y + artwork_size // 2 - max(4, int(8 * scale))
            draw.text((margin + max(4, int(8 * scale)), no_art_y), "No artwork", font=fonts["small"], fill=(200, 200, 210))

        # Draw title with appropriate character limit based on width
        max_chars = max(10, int(w / (8 * scale)))  # Rough estimate
        draw_title_line(draw, title, (margin, title_y), fonts["small"], max_chars=max_chars)

        # Draw controls
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
