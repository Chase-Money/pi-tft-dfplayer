"""Widget primitives for the v2 UI framework."""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from PIL import ImageDraw

from .events import UIEvent
from ..draw_utils_v2 import xywh_to_xyxy, clamp


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
    ) -> None:
        self.rect = rect
        self.label = label
        self.on_press = on_press
        self.fill = fill
        self.text_color = text_color
        self.radius = radius

    def draw(self, draw: ImageDraw.ImageDraw, font) -> None:
        x, y, w, h = self.rect
        draw.rounded_rectangle(xywh_to_xyxy(self.rect), radius=self.radius, fill=self.fill)
        label = self.label() if callable(self.label) else self.label
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (w - tw) // 2, y + (h - th) // 2), label, font=font, fill=self.text_color)

    def handle_event(self, event: UIEvent) -> bool:
        if event.type != "tap":
            return False
        pos = event.get_point()
        if not pos:
            return False
        if self._contains(pos):
            self.on_press()
            return True
        return False

    def _contains(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        rx, ry, rw, rh = self.rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh


class ListWidget:
    def __init__(self, items: Sequence[str], visible_rows: int = 5):
        self.items = list(items)
        self.visible_rows = max(1, visible_rows)
        self.selected_index = 0
        self.scroll = 0

    def move_selection(self, delta: int) -> None:
        if not self.items:
            return
        self.selected_index = clamp(self.selected_index + delta, 0, len(self.items) - 1)
        if self.selected_index < self.scroll:
            self.scroll = self.selected_index
        elif self.selected_index >= self.scroll + self.visible_rows:
            self.scroll = self.selected_index - self.visible_rows + 1

    def draw(self, draw: ImageDraw.ImageDraw, rect: Rect, font) -> None:
        x, y, w, h = rect
        row_h = max(1, h // self.visible_rows)
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


class SliderWidget:
    def __init__(self, rect: Rect, min_value: int = 0, max_value: int = 30):
        self.rect = rect
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value

    def draw(self, draw: ImageDraw.ImageDraw, font=None) -> None:
        x, y, w, h = self.rect
        draw.rounded_rectangle(xywh_to_xyxy((x, y, w, h)), radius=h // 2, fill=(55, 60, 75))
        fillw = int(w * (self.value - self.min_value) / max(1, self.max_value - self.min_value))
        draw.rounded_rectangle(xywh_to_xyxy((x, y, fillw, h)), radius=h // 2, fill=(230, 195, 80))
        if font:
            draw.text((x + w + 8, y - 4), f"{self.value:02d}", font=font, fill=(235, 235, 235))

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

