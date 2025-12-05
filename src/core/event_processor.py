"""Event processing coordinator for the v2 UI framework.

Handles conversion between hardware touch events and UI framework events.
"""

from typing import Any, Optional

from ui.framework.events import UIEvent


def _safe_attr(obj: Any, name: str, default: Optional[Any] = None) -> Optional[Any]:
    """Safely retrieve attribute without auto-creating Mock children."""
    if obj is None:
        return default
    try:
        data = getattr(obj, "__dict__", {})
        if isinstance(data, dict) and name in data:
            return data[name]
    except Exception:
        pass
    return getattr(obj, name, default)


class EventProcessor:
    """Processes touch events and converts them to UI events."""

    def touch_to_ui_event(self, touch_event) -> Optional[UIEvent]:
        """
        Convert a touch event to a UI event.

        Args:
            touch_event: Touch event from TouchController

        Returns:
            UIEvent or None if event type not recognized
        """
        event_type = _safe_attr(touch_event, "type")
        x = _safe_attr(touch_event, "x")
        y = _safe_attr(touch_event, "y")
        dx = _safe_attr(touch_event, "dx", 0) or 0
        dy = _safe_attr(touch_event, "dy", 0) or 0
        direction = _safe_attr(touch_event, "direction")
        raw_x = _safe_attr(touch_event, "raw_x")
        raw_y = _safe_attr(touch_event, "raw_y")

        raw = (raw_x, raw_y) if raw_x is not None and raw_y is not None else None

        if event_type == "tap":
            return UIEvent("tap", {"pos": (x, y), "raw": raw})
        if event_type == "drag":
            return UIEvent("drag", {"pos": (x, y), "dx": dx, "dy": dy, "raw": raw})
        if event_type == "swipe":
            return UIEvent("swipe", {"direction": direction, "delta": max(abs(dx), abs(dy)), "raw": raw})
        if event_type == "press":
            return UIEvent("press", {"pos": (x, y), "raw": raw})
        if event_type == "release":
            return UIEvent("release", {"pos": (x, y), "raw": raw})
        return None