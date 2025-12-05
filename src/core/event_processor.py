"""Event processing coordinator for the v2 UI framework.

Handles conversion between hardware touch events and UI framework events.
"""

from typing import Optional

from ui.framework.events import UIEvent


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
        event_type = getattr(touch_event, "type", None)
        x = getattr(touch_event, "x", None)
        y = getattr(touch_event, "y", None)
        dx = getattr(touch_event, "dx", 0)
        dy = getattr(touch_event, "dy", 0)
        direction = getattr(touch_event, "direction", None)
        raw_x = getattr(touch_event, "raw_x", None)
        raw_y = getattr(touch_event, "raw_y", None)

        # Include raw coordinates for calibration screen
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