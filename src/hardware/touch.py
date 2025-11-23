"""
Touch input handling for the DFPlayer GUI.
"""

import os
import select
import statistics
import time
from typing import Optional

try:
    from evdev import InputDevice, ecodes, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    InputDevice = None  # type: ignore
    ecodes = None  # type: ignore
    list_devices = None  # type: ignore

class TouchInput:
    def __init__(self, device_path=None):
        self.device = self._find_device(device_path)
        self.min_x, self.max_x, self.min_y, self.max_y = self._get_abs_info()
        self.screen_width = 480
        self.screen_height = 320
        self.orientation = dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=False)
        self.calibration = None

    def _find_device(self, device_path):
        """Find the touch device, preferring ADS7846/XPT2046 or any EV_ABS touchscreen."""
        if device_path and os.path.exists(device_path):
            return InputDevice(device_path)
        if os.path.exists("/dev/input/touchscreen"):
            return InputDevice("/dev/input/touchscreen")
        # Prefer named touch controllers
        for path in list_devices():
            dev = InputDevice(path)
            name = (dev.name or "").lower()
            if "ads7846" in name or "xpt2046" in name or "touch" in name:
                return dev
        # Fallback: pick first device that exposes ABS_X/ABS_Y + BTN_TOUCH
        for path in list_devices():
            dev = InputDevice(path)
            caps = dev.capabilities() if hasattr(dev, "capabilities") else {}
            abs_caps = caps.get(ecodes.EV_ABS, [])
            key_caps = caps.get(ecodes.EV_KEY, [])
            if ecodes.ABS_X in abs_caps and ecodes.ABS_Y in abs_caps and ecodes.BTN_TOUCH in key_caps:
                return dev
        devs = list_devices()
        if not devs:
            raise RuntimeError("No input event devices found")
        return InputDevice(devs[0])

    def _get_abs_info(self):
        """Get the absolute axis information from the touch device."""
        if self.device:
            ax = self.device.absinfo(ecodes.ABS_X)
            ay = self.device.absinfo(ecodes.ABS_Y)
            if ax and ay:
                return ax.min, ax.max, ay.min, ay.max
        return 0, 4095, 0, 4095

    def fileno(self):
        return self.device.fileno() if self.device else -1

    def read_event(self):
        """Read all available touch events from the device."""
        if not self.device:
            return []
        try:
            events = self.device.read()
            return events or []
        except BlockingIOError:
            return []

    def scale_xy(
        self,
        x,
        y,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        orientation: Optional[dict] = None,
        calibration: Optional[tuple] = None,
    ):
        """Scale raw touch coordinates to screen coordinates.

        Args are optional to preserve the previous API. When not supplied, the
        values recorded on the TouchInput instance are used.
        """
        screen_width = screen_width or self.screen_width
        screen_height = screen_height or self.screen_height
        orientation = orientation or self.orientation
        cal = calibration or self.calibration
        if cal:
            min_x, max_x, min_y, max_y = cal
        else:
            min_x, max_x, min_y, max_y = self.min_x, self.max_x, self.min_y, self.max_y

        if orientation.get("SWAP_XY"):
            x, y = y, x
            # When swapping axes, also swap target dimensions
            screen_width, screen_height = screen_height, screen_width
        if orientation.get("FLIP_X"):
            x = max_x - (x - min_x)
        if orientation.get("FLIP_Y"):
            y = max_y - (y - min_y)

        if max_x == min_x: max_x = min_x + 1
        if max_y == min_y: max_y = min_y + 1

        sx = int((x - min_x) * (screen_width - 1) / (max_x - min_x))
        sy = int((y - min_y) * (screen_height - 1) / (max_y - min_y))

        return max(0, min(screen_width - 1, sx)), max(0, min(screen_height - 1, sy))

    def wait_for_touch(self, timeout=8.0, samples=18):
        """
        Wait for a touch event and return the median coordinates.

        Uses select() to avoid blocking indefinitely. Returns None if timeout expires.

        Args:
            timeout: Maximum time to wait in seconds (default: 8.0)
            samples: Number of coordinate samples to collect (default: 18)

        Returns:
            tuple: (x, y) median coordinates, or None if timeout
        """
        t0 = time.time()
        touching = False
        buf_x, buf_y = [], []

        while True:
            remaining = timeout - (time.time() - t0)
            if remaining <= 0:
                return None

            # Use select() to check for available data with timeout
            try:
                ready, _, _ = select.select([self.device], [], [], min(remaining, 0.1))
                if not ready:
                    continue  # Timeout on select, check overall timeout and retry
            except Exception:
                return None

            # Read available events
            try:
                events = self.device.read()
                if callable(events):
                    events = events()
            except BlockingIOError:
                continue

            # Process events
            for ev in events:
                if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                    touching = (ev.value == 1)
                    if not touching:
                        buf_x.clear()
                        buf_y.clear()
                elif ev.type == ecodes.EV_ABS:
                    if ev.code == ecodes.ABS_X:
                        buf_x.append(ev.value)
                    elif ev.code == ecodes.ABS_Y:
                        buf_y.append(ev.value)
                    if len(buf_x) >= samples and len(buf_y) >= samples:
                        return int(statistics.median(buf_x)), int(statistics.median(buf_y))

            # If we have partial samples for both axes, return the median so far
            if touching and buf_x and buf_y:
                return int(statistics.median(buf_x)), int(statistics.median(buf_y))
