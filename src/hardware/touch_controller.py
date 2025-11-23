"""
Touch controller wrapper for V2 framework integration.

Provides event-based touch handling compatible with the UI framework.
"""

import logging
import select
import time
from dataclasses import dataclass
from typing import List, Optional

from .touch import TouchInput

logger = logging.getLogger(__name__)


@dataclass
class TouchEvent:
    """Touch event data class."""
    type: str  # 'tap', 'drag', 'swipe', 'press', 'release'
    x: int
    y: int
    dx: int = 0
    dy: int = 0
    direction: Optional[str] = None  # 'up', 'down', 'left', 'right'
    timestamp: float = 0.0
    raw_x: Optional[int] = None
    raw_y: Optional[int] = None


class TouchController:
    """
    High-level touch controller for event-based input.

    Converts raw touch device events into higher-level touch events
    (tap, drag, swipe) suitable for UI framework consumption.
    """

    def __init__(self, device: Optional[str] = None, config=None):
        """
        Initialize the touch controller.

        Args:
            device: Touch device path (default: auto-detect)
            config: Config instance for loading threshold settings (optional)
        """
        try:
            self.touch = TouchInput(device_path=device)
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize touch input: {e}")
            self.touch = None
            self.available = False

        # Touch state tracking
        self.is_pressed = False
        self.press_x = 0
        self.press_y = 0
        self.press_time = 0.0
        self.last_x = 0
        self.last_y = 0

        # Load gesture thresholds from config or use defaults
        if config:
            thresholds = config.get_touch_thresholds()
            self.tap_threshold_ms = thresholds.get("tap_threshold_ms", 400)
            self.drag_threshold_px = thresholds.get("drag_threshold_px", 12)
            self.swipe_threshold_px = thresholds.get("swipe_threshold_px", 48)
        else:
            # Defaults tuned for responsiveness on resistive panels
            self.tap_threshold_ms = 400
            self.drag_threshold_px = 12
            self.swipe_threshold_px = 48

    def get_events(self, timeout: float = 0.0) -> List[TouchEvent]:
        """
        Get pending touch events.

        Args:
            timeout: Timeout in seconds (0 = non-blocking)

        Returns:
            List of TouchEvent objects
        """
        if not self.available or not self.touch:
            logger.debug("[TOUCHCTRL] get_events: not available or no touch device")
            return []

        events = []

        # Use select to check for available data
        try:
            ready, _, _ = select.select([self.touch], [], [], timeout)
            if not ready:
                return []
            logger.debug("[TOUCHCTRL] select() found data ready")
        except Exception as e:
            logger.error(f"Error in select: {e}")
            return []

        # Read all available events
        try:
            event_batch = self.touch.read_event()
            logger.debug(f"[TOUCHCTRL] read_event() returned {len(event_batch)} events")
            # Normalize to list
            if not isinstance(event_batch, (list, tuple)):
                event_batch = [event_batch] if event_batch else []
            for evt in event_batch:
                logger.debug(f"[TOUCHCTRL] Processing raw event: type={evt.type}, code={evt.code}, value={evt.value}")
                touch_evt = self._process_raw_event(evt)
                if touch_evt:
                    logger.debug(f"[TOUCHCTRL] Created touch event: {touch_evt.type} at ({touch_evt.x}, {touch_evt.y})")
                    events.append(touch_evt)
        except Exception as e:
            logger.error(f"Error reading touch events: {e}", exc_info=True)

        return events

    def _process_raw_event(self, raw_event) -> Optional[TouchEvent]:
        """
        Process a raw evdev event into a TouchEvent.

        Args:
            raw_event: Raw event from evdev

        Returns:
            TouchEvent or None
        """
        try:
            from evdev import ecodes
        except ImportError:
            return None

        # Track absolute X/Y position
        if raw_event.type == ecodes.EV_ABS:
            if raw_event.code == ecodes.ABS_X:
                self.last_x = raw_event.value
            elif raw_event.code == ecodes.ABS_Y:
                self.last_y = raw_event.value

        # Detect press/release
        elif raw_event.type == ecodes.EV_KEY:
            if raw_event.code == ecodes.BTN_TOUCH:
                if raw_event.value == 1:  # Press
                    return self._handle_press()
                elif raw_event.value == 0:  # Release
                    return self._handle_release()

        return None

    def _handle_press(self) -> Optional[TouchEvent]:
        """Handle touch press event."""
        # Scale coordinates
        sx, sy = self.touch.scale_xy(self.last_x, self.last_y)

        logger.info(f"[TOUCHCTRL] Press: raw=({self.last_x}, {self.last_y}) → scaled=({sx}, {sy})")

        self.is_pressed = True
        self.press_x = sx
        self.press_y = sy
        self.press_time = time.time()

        return TouchEvent(
            type="press",
            x=sx,
            y=sy,
            timestamp=self.press_time,
            raw_x=self.last_x,
            raw_y=self.last_y,
        )

    def _handle_release(self) -> Optional[TouchEvent]:
        """Handle touch release event."""
        if not self.is_pressed:
            return None

        # Scale coordinates
        sx, sy = self.touch.scale_xy(self.last_x, self.last_y)

        release_time = time.time()
        duration_ms = (release_time - self.press_time) * 1000

        dx = sx - self.press_x
        dy = sy - self.press_y
        distance = (dx**2 + dy**2) ** 0.5

        self.is_pressed = False

        # Determine gesture type
        if duration_ms < self.tap_threshold_ms and distance < self.drag_threshold_px:
            # Tap gesture
            return TouchEvent(
                type="tap",
                x=self.press_x,
                y=self.press_y,
                timestamp=release_time,
                raw_x=self.last_x,
                raw_y=self.last_y,
            )

        elif distance >= self.swipe_threshold_px:
            # Swipe gesture
            direction = self._get_swipe_direction(dx, dy)
            return TouchEvent(
                type="swipe",
                x=sx,
                y=sy,
                dx=dx,
                dy=dy,
                direction=direction,
                timestamp=release_time,
                raw_x=self.last_x,
                raw_y=self.last_y,
            )

        else:
            # Drag gesture
            return TouchEvent(
                type="drag",
                x=sx,
                y=sy,
                dx=dx,
                dy=dy,
                timestamp=release_time,
                raw_x=self.last_x,
                raw_y=self.last_y,
            )

    def _get_swipe_direction(self, dx: int, dy: int) -> str:
        """
        Determine swipe direction from delta.

        Args:
            dx: X delta
            dy: Y delta

        Returns:
            Direction string: 'up', 'down', 'left', 'right'
        """
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"

    def set_calibration(self, min_x: int, max_x: int, min_y: int, max_y: int) -> None:
        """
        Set touch calibration values.

        Args:
            min_x: Minimum X value
            max_x: Maximum X value
            min_y: Minimum Y value
            max_y: Maximum Y value
        """
        if self.touch:
            self.touch.calibration = (min_x, max_x, min_y, max_y)
            logger.info(f"Touch calibration set: ({min_x}, {max_x}, {min_y}, {max_y})")

    def set_orientation(self, swap_xy: bool = False, flip_x: bool = False, flip_y: bool = False) -> None:
        """
        Set touch orientation.

        Args:
            swap_xy: Swap X and Y axes
            flip_x: Flip X axis
            flip_y: Flip Y axis
        """
        if self.touch:
            self.touch.orientation = {
                "SWAP_XY": swap_xy,
                "FLIP_X": flip_x,
                "FLIP_Y": flip_y
            }
            logger.info(f"Touch orientation set: swap={swap_xy}, flip_x={flip_x}, flip_y={flip_y}")

    def close(self) -> None:
        """Close the touch controller."""
        if self.touch and hasattr(self.touch, 'device'):
            try:
                if hasattr(self.touch.device, 'close'):
                    self.touch.device.close()
            except Exception as e:
                logger.error(f"Error closing touch device: {e}")
