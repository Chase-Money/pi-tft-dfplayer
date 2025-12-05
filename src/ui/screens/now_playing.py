"""Now playing screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework.manager import ScreenView
from ..framework.widgets import ButtonWidget, SliderWidget, ArtworkWidget
from ..framework.events import UIEvent
from ..draw_utils import clamp
from ..views import (
    draw_play_indicator,
    draw_track_number,
    draw_title_line,
    draw_volume_bar,
    draw_status_banner,
)
from ..theme_palette import get_palette
from ..framework.debug import debug_tap_logging_enabled


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
        self.artwork_widget = None
        self._last_resolution = None

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        w, h = image.width, image.height
        scale = context["scale"]

        palette = get_palette()
        # Clear background
        draw.rectangle((0, 0, w, h), fill=palette.bg)

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
        # Increase spacing between slider and button to prevent hit area overlap
        button_y = slider_y + slider_h + max(12, int(18 * scale))

        dbg = debug_tap_logging_enabled()
        # Create widgets dynamically based on resolution
        # Position back button on right side to avoid interfering with play indicator
        back_x = w - margin - back_w
        self.back_button = ButtonWidget((back_x, small_margin, back_w, button_h), "Back", self.manager.pop, debug_log=dbg)
        self.play_button = ButtonWidget((margin, button_y, play_w, button_h), self._play_label, self._toggle_play, debug_log=dbg)
        self.slider = SliderWidget((margin, slider_y, int(w * 0.7), slider_h))

        # Draw back button
        self.back_button.draw(draw, fonts["small"])

        if not self.state:
            draw.text((margin, info_y), "State not available", font=fonts["medium"], fill=palette.danger)
            return

        track = self.state.get_playing_track() or self.state.get_selected_track()
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

        # Create/update artwork widget if needed
        artwork_rect = (margin, artwork_y, artwork_size, artwork_size)
        if not self.artwork_widget or self.artwork_widget.rect != artwork_rect:
            self.artwork_widget = ArtworkWidget(artwork_rect)

        # Set and draw artwork
        self.artwork_widget.set_artwork(artwork, self.state)
        self.artwork_widget.draw(image, draw, fonts["small"], palette)

        # Draw title with appropriate character limit based on width
        max_chars = max(10, int(w / (8 * scale)))  # Rough estimate
        draw_title_line(draw, title, (margin, title_y), fonts["small"], max_chars=max_chars)

        # Draw controls
        self.play_button.draw(draw, fonts["small"])
        self.slider.draw(draw, fonts["small"])
        # Track a coarse dirty region (controls + artwork area)
        self.last_dirty = [
            (margin, artwork_y, artwork_size, artwork_size),
            (margin, button_y, play_w, button_h),
            (margin, slider_y, int(w * 0.7), slider_h + button_h + max(8, int(12 * scale))),
        ]

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
            if self.state.get_playing_track() is not None:
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
        # Reduce vertical expansion to avoid interfering with play button below
        return rx <= x <= rx + rw and ry - 8 <= y <= ry + rh + 4

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
