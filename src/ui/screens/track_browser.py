"""Track browser screen (v2) placeholder."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..framework.manager import ScreenView
from ..framework.widgets import ListWidget, ButtonWidget
from ..framework.events import UIEvent
from ..views import draw_status_banner
from ..theme_palette import get_palette
from ..framework.debug import debug_tap_logging_enabled


class TrackBrowserScreen(ScreenView):
    name = "track_browser"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.state = services.get("state") if services else None
        self.backend = services.get("backend") if services else None
        self.list_widget = ListWidget([], visible_rows=4)
        # Widgets will be created dynamically in render based on resolution
        self.back_button = None
        self._last_resolution = None
        self.list_rect = (0, 0, 0, 0)  # Will be calculated in render
        self._scrolling = False
        self._last_drag_delta = 0.0

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
        title_y = max(4, int(12 * scale))
        list_y = max(24, int(60 * scale))

        # Only recreate widgets if resolution changed
        current_res = (w, h)
        if current_res != self._last_resolution:
            dbg = debug_tap_logging_enabled()
            self.back_button = ButtonWidget((margin, small_margin, back_w, button_h), "Back", self.manager.pop, debug_log=dbg)
            self._last_resolution = current_res

        # Draw title centered (or offset for smaller screens)
        title_x = max(margin, int(w * 0.3))
        draw.text((title_x, title_y), "Tracks", font=fonts["medium"], fill=palette.text)

        # Draw back button
        self.back_button.draw(draw, fonts["small"])

        # Calculate list area (use most of remaining space)
        list_bottom_margin = max(8, int(20 * scale))
        self.list_rect = (margin, list_y, w - 2 * margin, h - list_y - list_bottom_margin)

        # Calculate visible rows based on list height and row height
        visible_rows = max(1, self.list_rect[3] // self.list_widget.row_height)
        self.list_widget.set_visible_rows(visible_rows)

        # Update list state
        if self.state:
            self.list_widget.selected_index = self.state.playback.selected_track_index
            # Scroll position auto-managed by ListWidget - no need to restore from state

        # Draw list
        self.list_widget.draw(draw, self.list_rect, fonts["small"])
        self.last_dirty = [self.list_rect]

    def handle_event(self, event: UIEvent) -> bool:
        if event.type == "drag":
            pos = event.get_point()
            dx = (event.payload or {}).get("dx", 0)
            dy = (event.payload or {}).get("dy", 0)
            if pos and self._point_in_list(pos):
                if self._scroll_list(-dy):
                    self._scrolling = True
                    self._last_drag_delta = -dy
                    return True
                self._scrolling = False
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
        if self._scrolling and event.type == "tap":
            # Swallow tap immediately after a drag to avoid accidental activation
            self._scrolling = False
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
