"""Track browser screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework_v2.manager import ScreenView
from ..framework_v2.widgets import ListWidget, ButtonWidget
from ..framework_v2.events import UIEvent


class TrackBrowserScreen(ScreenView):
    name = "track_browser"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.state = services.get("state") if services else None
        self.backend = services.get("backend") if services else None
        self.list_widget = ListWidget([], visible_rows=4)
        self.back_button = ButtonWidget((16, 4, 80, 40), "Back", self.manager.pop)
        self.list_rect = (16, 60, 224, 200)
        self._scrolling = False

    def on_enter(self, **kwargs) -> None:
        """Ensure the list is up-to-date when the screen is shown."""
        if self.state and self.state.tracks:
            labels = [f"{t.number:03d} {t.title}" for t in self.state.tracks]
            self.list_widget.set_items(labels)
        else:
            self.list_widget.set_items(["No tracks available"])

    def render(self, context: dict) -> None:
        image: Image.Image = context["image"]
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        draw.rectangle((0, 0, image.width, image.height), fill=(12, 16, 24))
        draw.text((110, 12), "Tracks", font=fonts["medium"], fill=(235, 235, 235))
        self.back_button.draw(draw, fonts["small"])

        self.list_rect = (16, 60, image.width - 32, image.height - 80)
        visible_rows = max(1, self.list_rect[3] // self.list_widget.row_height)
        self.list_widget.set_visible_rows(visible_rows)

        if self.state:
            self.list_widget.selected_index = self.state.playback.selected_track_index
            max_scroll = max(0, len(self.state.tracks) - visible_rows)
            self.list_widget.scroll = min(max(self.state.playback.track_scroll_pos, 0), max_scroll)
        
        self.list_widget.draw(draw, self.list_rect, fonts["small"])

    def handle_event(self, event: UIEvent) -> bool:
        if event.type == "drag":
            pos = event.get_point()
            prev = (event.payload or {}).get("prev")
            if pos and prev and self._point_in_list(pos):
                delta_px = pos[1] - prev[1]
                if self._scroll_list(delta_px):
                    self._scrolling = True
                    return True
        if event.type == "drag_end":
            if self._scrolling:
                self._scrolling = False
                return True
        if event.type == "swipe":
            payload = event.payload or {}
            delta = payload.get("delta", 0)
            self.list_widget.move_selection(delta)
            self._apply_selection()
            return True
        if self.back_button.handle_event(event):
            return True
        if event.type == "tap" and not self._scrolling:
            pos = event.get_point()
            if pos:
                idx = self.list_widget.tap(self.list_rect, pos)
                if idx is not None:
                    self._play_index(idx)
                    # Navigate to now playing screen after selection
                    self.manager.push("now_playing")
                    return True
        return False

    def _play_index(self, idx: int) -> None:
        if not self.state or not self.backend:
            return
        
        track = self.state.select_track_index(idx)
        if not track:
            return
            
        self.backend.play_track(track.number)
        self.state.start_playback(idx)

    def _apply_selection(self) -> None:
        if not self.state:
            return
        idx = self.list_widget.selected_index
        self.state.select_track_index(idx)
        self.state.playback.track_scroll_pos = self.list_widget.scroll

    def _scroll_list(self, delta_px: float) -> bool:
        changed = self.list_widget.scroll_pixels(-delta_px)
        if changed and self.state:
            self.state.playback.track_scroll_pos = self.list_widget.scroll
        return changed

    def _point_in_list(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        rx, ry, rw, rh = self.list_rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh
