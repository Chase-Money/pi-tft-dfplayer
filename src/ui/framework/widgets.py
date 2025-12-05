"""Widget primitives for the v2 UI framework."""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional, Sequence, Tuple

from PIL import ImageDraw

from .events import UIEvent
from ..draw_utils import xywh_to_xyxy, clamp

logger = logging.getLogger(__name__)


Rect = Tuple[int, int, int, int]


class ButtonWidget:
    def __init__(
        self,
        rect: Rect,
        label: str | Callable[[], str],
        on_press: Callable[[], None],
        fill=(80, 110, 185),
        text_color=(255, 255, 255),
        radius: int = 16,
        debug_log: bool = False,
    ) -> None:
        self.rect = rect
        self.label = label
        self.on_press = on_press
        self.fill = fill
        self.text_color = text_color
        self.radius = radius
        self._flash_until = 0.0
        self._pressed = False
        self._debug_log = debug_log

    def draw(self, draw: ImageDraw.ImageDraw, font) -> None:
        x, y, w, h = self.rect
        fill = self.fill

        # Pressed state: darken the button slightly
        if self._pressed:
            r, g, b = self.fill
            fill = (max(0, int(r * 0.7)), max(0, int(g * 0.7)), max(0, int(b * 0.7)))
        # Flash state: brighten the button
        elif time.monotonic() < self._flash_until:
            r, g, b = self.fill
            fill = (min(255, int(r + (255 - r) * 0.35)),
                    min(255, int(g + (255 - g) * 0.35)),
                    min(255, int(b + (255 - b) * 0.35)))

        draw.rounded_rectangle(xywh_to_xyxy(self.rect), radius=self.radius, fill=fill)
        label = self.label() if callable(self.label) else self.label
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (w - tw) // 2, y + (h - th) // 2), label, font=font, fill=self.text_color)
        if self._debug_log:
            logger.debug(f"[BTN] rect={self.rect} label={label}")

    def handle_event(self, event: UIEvent) -> bool:
        pos = event.get_point()
        if not pos:
            return False

        label = self.label if isinstance(self.label, str) else self.label()

        # Press event: show visual feedback only (don't trigger action yet)
        # This allows user to cancel by dragging away before release
        if event.type == "press":
            if self._contains(pos, expand=4):
                self._pressed = True
                if self._debug_log:
                    logger.debug(f"[BTN] '{label}' pressed at {pos}, rect={self.rect}")
                return True
            return False

        # Drag event: cancel if user drags outside button bounds
        if event.type == "drag":
            if self._pressed and not self._contains(pos, expand=4):
                self._pressed = False  # Cancel press if drag goes outside
                if self._debug_log:
                    logger.debug(f"[BTN] '{label}' press cancelled by drag outside bounds at {pos}")
                return True
            return self._pressed  # Consume drag events while pressed

        # Release event: trigger action if still pressed and release is in bounds
        # This handles case where user pressed button but finger jittered (drag detected)
        # but release is still within button - should activate
        if event.type == "release":
            if self._pressed:
                self._pressed = False
                if self._contains(pos, expand=4):
                    # User released inside button - trigger action
                    if self._debug_log:
                        logger.debug(f"[BTN] '{label}' activated on release at {pos}, rect={self.rect}")
                    self.on_press()
                    self._flash_until = time.monotonic() + 0.15
                    return True
                else:
                    # User released outside button - cancel action
                    if self._debug_log:
                        logger.debug(f"[BTN] '{label}' press cancelled by release outside bounds at {pos}")
                    return True
            # No active press - check if this is a direct release within bounds (could activate)
            # This handles resistive touchscreens where press might be missed but release detected
            if self._contains(pos, expand=4):
                if self._debug_log:
                    logger.debug(f"[BTN] '{label}' activated on direct release at {pos}, rect={self.rect}")
                self.on_press()
                self._flash_until = time.monotonic() + 0.15
                return True
            return False

        # Tap event: trigger action if in bounds (original tap behavior)
        if event.type == "tap":
            if self._contains(pos, expand=4):
                self._pressed = False
                if self._debug_log:
                    logger.debug(f"[BTN] '{label}' activated on tap at {pos}, rect={self.rect}")
                self.on_press()
                self._flash_until = time.monotonic() + 0.15
                return True
            return False

        return False

    def _contains(self, pos: Tuple[int, int], expand: int = 0) -> bool:
        x, y = pos
        rx, ry, rw, rh = self.rect
        return (rx - expand) <= x <= (rx + rw + expand) and (ry - expand) <= y <= (ry + rh + expand)


class ListWidget:
    def __init__(self, items: Sequence[str], visible_rows: int = 5):
        self.items = list(items)
        self.visible_rows = max(1, visible_rows)
        self.selected_index = 0
        self.scroll = 0
        self.row_height = 32
        self._scroll_fraction = 0.0

    def set_items(self, items: Sequence[str]) -> None:
        self.items = list(items)
        if not self.items:
            self.selected_index = 0
            self.scroll = 0
            self._scroll_fraction = 0.0
            return
        self.selected_index = min(self.selected_index, len(self.items) - 1)
        self.scroll = min(self.scroll, max(0, len(self.items) - self.visible_rows))
        self._scroll_fraction = 0.0

    def set_visible_rows(self, rows: int) -> None:
        self.visible_rows = max(1, rows)
        self.scroll = min(self.scroll, max(0, len(self.items) - self.visible_rows))

    def move_selection(self, delta: int) -> None:
        if not self.items:
            return
        self.selected_index = clamp(self.selected_index + delta, 0, len(self.items) - 1)
        if self.selected_index < self.scroll:
            self.scroll = self.selected_index
        elif self.selected_index >= self.scroll + self.visible_rows:
            self.scroll = self.selected_index - self.visible_rows + 1

    def scroll_pixels(self, delta_px: float) -> bool:
        if not self.items:
            return False
        if self.row_height <= 0:
            return False
        self._scroll_fraction += delta_px / max(1, self.row_height)
        step = int(self._scroll_fraction)
        if step == 0:
            return False
        self._scroll_fraction -= step
        max_scroll = max(0, len(self.items) - self.visible_rows)
        new_scroll = clamp(self.scroll + step, 0, max_scroll)
        if new_scroll == self.scroll:
            return False
        self.scroll = new_scroll
        return True

    def draw(self, draw: ImageDraw.ImageDraw, rect: Rect, font) -> None:
        x, y, w, h = rect
        row_h = max(1, h // self.visible_rows)
        self.row_height = row_h
        for row in range(self.visible_rows):
            idx = self.scroll + row
            if idx >= len(self.items):
                break
            label = self.items[idx]
            row_rect = (x, y + row * row_h, w, row_h - 4)
            fill = (45, 48, 60)
            text_color = (220, 220, 220)
            if idx == self.selected_index:
                fill = (215, 165, 60)
                text_color = (25, 25, 25)
            draw.rounded_rectangle(xywh_to_xyxy(row_rect), radius=8, fill=fill)
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((row_rect[0] + 8, row_rect[1] + (row_rect[3] - th) // 2), label[:28], font=font, fill=text_color)

    def tap(self, rect: Rect, pos: Tuple[int, int]) -> Optional[int]:
        rx, ry, rw, rh = rect
        px, py = pos
        if not (rx <= px <= rx + rw and ry <= py <= ry + rh):
            return None
        row_h = max(1, rh // self.visible_rows)
        row = (py - ry) // row_h
        idx = self.scroll + int(row)
        if 0 <= idx < len(self.items):
            self.selected_index = idx
            return idx
        return None


class SliderWidget:
    def __init__(self, rect: Rect, min_value: int = 0, max_value: int = 30):
        self.rect = rect
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        self.display_value = float(self.value)

    def draw(self, draw: ImageDraw.ImageDraw, font=None) -> None:
        x, y, w, h = self.rect
        draw.rounded_rectangle(xywh_to_xyxy((x, y, w, h)), radius=h // 2, fill=(55, 60, 75))
        self.display_value += (self.value - self.display_value) * 0.2
        self.display_value = max(self.min_value, min(self.max_value, self.display_value))
        fillw = int(w * (self.display_value - self.min_value) / max(1, self.max_value - self.min_value))
        draw.rounded_rectangle(xywh_to_xyxy((x, y, fillw, h)), radius=h // 2, fill=(230, 195, 80))
        if font:
            draw.text((x + w + 8, y - 4), f"{int(round(self.display_value)):02d}", font=font, fill=(235, 235, 235))

    def handle_event(self, event: UIEvent) -> bool:
        if event.type != "drag":
            return False
        pos = event.get_point()
        if not pos:
            return False
        x, _ = pos
        self.value = self.value_from_x(x)
        return True

    def value_from_x(self, x: int) -> int:
        rx, _, rw, _ = self.rect
        clamped = clamp(x, rx, rx + rw)
        ratio = (clamped - rx) / max(1, rw)
        return int(round(self.min_value + ratio * (self.max_value - self.min_value)))


class ArtworkWidget:
    """Widget for displaying album artwork with caching."""

    def __init__(self, rect: Rect):
        """Initialize artwork widget.

        Args:
            rect: (x, y, width, height) for the artwork display area
        """
        self.rect = rect
        self._current_artwork_path: Optional[str] = None
        self._cached_thumbnail: Optional[any] = None

    def set_artwork(self, artwork_path: Optional[str], state=None) -> None:
        """Set the artwork to display.

        Args:
            artwork_path: Path to artwork image file, or None for no artwork
            state: Optional ApplicationState for caching
        """
        if artwork_path == self._current_artwork_path:
            return  # Already loaded

        self._current_artwork_path = artwork_path
        self._cached_thumbnail = None

        if not artwork_path:
            return

        # Check state cache first
        if state:
            cached = state.get_cached_artwork(artwork_path)
            if cached:
                self._cached_thumbnail = cached
                return

        # Load and cache
        try:
            from utils.metadata import load_artwork_thumbnail
            x, y, w, h = self.rect
            size = (w, h)
            thumbnail = load_artwork_thumbnail(artwork_path, size=size)
            if thumbnail:
                self._cached_thumbnail = thumbnail
                if state:
                    state.cache_artwork(artwork_path, thumbnail)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load artwork {artwork_path}: {e}")
            self._cached_thumbnail = None

    def draw(self, image, draw: ImageDraw.ImageDraw, font=None, palette=None) -> None:
        """Draw the artwork or placeholder.

        Args:
            image: PIL Image to paste artwork onto
            draw: PIL ImageDraw for drawing placeholder
            font: Font for "No artwork" text
            palette: Theme palette for colors
        """
        x, y, w, h = self.rect

        if self._cached_thumbnail:
            # Paste artwork
            try:
                image.paste(self._cached_thumbnail, (x, y))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to paste artwork: {e}")
                self._draw_placeholder(draw, font, palette)
        else:
            self._draw_placeholder(draw, font, palette)

    def _draw_placeholder(self, draw: ImageDraw.ImageDraw, font=None, palette=None) -> None:
        """Draw a placeholder when no artwork is available."""
        x, y, w, h = self.rect

        # Get colors from palette or use defaults
        if palette:
            outline_color = getattr(palette, 'accent_alt', (100, 120, 150))
            text_color = getattr(palette, 'text_dim', (140, 140, 140))
        else:
            outline_color = (100, 120, 150)
            text_color = (140, 140, 140)

        # Draw outline
        draw.rectangle((x, y, x + w, y + h), outline=outline_color, width=2)

        # Draw "No artwork" text
        if font:
            text = "No artwork"
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                text_x = x + (w - tw) // 2
                text_y = y + (h - th) // 2
                draw.text((text_x, text_y), text, font=font, fill=text_color)
            except Exception:
                # Fallback if textbbox fails
                draw.text((x + 8, y + h // 2 - 8), text, font=font, fill=text_color)
