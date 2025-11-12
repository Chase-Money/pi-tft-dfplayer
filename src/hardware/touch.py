"""Touch input module for resistive touchscreen.

Handles XPT2046/ADS7846 touch controller input via evdev with support for:
- 8 orientation configurations (SWAP_XY, FLIP_X, FLIP_Y combinations)
- Four-point calibration
- Median filtering for stability
"""

import logging
import os
import statistics
import time

logger = logging.getLogger(__name__)

# Conditional import for evdev (may not be available on all platforms)
try:
    from evdev import InputDevice, ecodes, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    logger.warning("evdev not available - touch input will not work")


class TouchInput:
    """Touch input manager for resistive touchscreen.

    Manages touch device initialization, calibration, orientation transforms,
    and coordinate scaling from raw touch values to screen coordinates.

    Attributes:
        screen_width: Display width in pixels
        screen_height: Display height in pixels
        orientation_index: Current orientation configuration (0-7)
        calibration: Calibration bounds (minx, maxx, miny, maxy) or None
    """

    # 8 orientation combinations (SWAP_XY, FLIP_X, FLIP_Y)
    ORIENTATIONS = [
        dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=False),
        dict(SWAP_XY=False, FLIP_X=True,  FLIP_Y=False),
        dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=True),
        dict(SWAP_XY=False, FLIP_X=True,  FLIP_Y=True),
        dict(SWAP_XY=True,  FLIP_X=False, FLIP_Y=False),
        dict(SWAP_XY=True,  FLIP_X=True,  FLIP_Y=False),
        dict(SWAP_XY=True,  FLIP_X=False, FLIP_Y=True),
        dict(SWAP_XY=True,  FLIP_X=True,  FLIP_Y=True),
    ]

    def __init__(self, screen_width=480, screen_height=320):
        """Initialize touch input manager.

        Args:
            screen_width: Display width in pixels
            screen_height: Display height in pixels
        """
        if not EVDEV_AVAILABLE:
            logger.error("evdev not available - touch input cannot be initialized")
            self._device = None
            self.driver_minx = 0
            self.driver_maxx = 4095
            self.driver_miny = 0
            self.driver_maxy = 4095
        else:
            self._device = None
            self.driver_minx = 0
            self.driver_maxx = 4095
            self.driver_miny = 0
            self.driver_maxy = 4095
            self._connect()

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.orientation_index = 6  # Default orientation
        self.calibration = None  # (minx, maxx, miny, maxy) or None

    def _find_touch_device(self):
        """Find touch input device.

        Returns:
            InputDevice: Touch device or None if not found
        """
        if not EVDEV_AVAILABLE:
            return None

        # Check for named touchscreen device first
        if os.path.exists("/dev/input/touchscreen"):
            try:
                return InputDevice("/dev/input/touchscreen")
            except Exception as e:
                logger.warning(f"Could not open /dev/input/touchscreen: {e}")

        # Search for ADS7846 or XPT2046 by name
        for devpath in list_devices():
            try:
                dev = InputDevice(devpath)
                name = (dev.name or "").lower()
                if "ads7846" in name or "xpt2046" in name:
                    logger.info(f"Found touch device: {dev.name} at {devpath}")
                    return dev
            except Exception:
                continue

        # Fallback to first available device
        devs = list_devices()
        if devs:
            logger.warning("Using first available input device as touch")
            return InputDevice(devs[0])

        return None

    def _connect(self):
        """Initialize touch device with error handling."""
        if not EVDEV_AVAILABLE:
            return

        try:
            self._device = self._find_touch_device()
            if self._device is None:
                raise RuntimeError("No input event devices found")

            # Read driver absolute axis ranges
            ax = self._device.absinfo(ecodes.ABS_X)
            ay = self._device.absinfo(ecodes.ABS_Y)

            if ax is None or ay is None:
                logger.error(f"Touch device lacks ABS axes: {self._device.path} {self._device.name}")
                logger.error("Touch input will not work properly")
                self._device = None
                return

            self.driver_minx, self.driver_maxx = ax.min, ax.max
            self.driver_miny, self.driver_maxy = ay.min, ay.max

            logger.info(f"Touch device initialized: {self._device.name}")
            logger.info(f"Driver ranges: X[{self.driver_minx}..{self.driver_maxx}] Y[{self.driver_miny}..{self.driver_maxy}]")

        except RuntimeError as e:
            logger.error(f"Failed to initialize touch device: {e}")
            logger.error("Touch input will not work. Ensure touch device is connected.")
            self._device = None
        except PermissionError as e:
            logger.error(f"Permission denied accessing touch device: {e}")
            logger.error("Try: sudo usermod -a -G input $USER")
            self._device = None
        except Exception as e:
            logger.error(f"Unexpected error initializing touch device: {e}")
            self._device = None

    def scale_xy(self, raw_x, raw_y):
        """Transform raw touch coordinates to screen coordinates.

        Applies orientation transforms and calibration scaling.

        Args:
            raw_x: Raw X coordinate from touch controller
            raw_y: Raw Y coordinate from touch controller

        Returns:
            tuple: (screen_x, screen_y) in pixel coordinates
        """
        # Use calibration if available, otherwise driver ranges
        if self.calibration:
            minx, maxx, miny, maxy = self.calibration
        else:
            minx, maxx = self.driver_minx, self.driver_maxx
            miny, maxy = self.driver_miny, self.driver_maxy

        # Apply orientation transforms
        orient = self.ORIENTATIONS[self.orientation_index]
        x, y = raw_x, raw_y

        if orient["SWAP_XY"]:
            x, y = y, x

        if orient["FLIP_X"]:
            x = maxx - (x - minx)

        if orient["FLIP_Y"]:
            y = maxy - (y - miny)

        # Prevent division by zero
        if maxx == minx:
            maxx = minx + 1
        if maxy == miny:
            maxy = miny + 1

        # Scale to screen coordinates
        sx = int((x - minx) * (self.screen_width - 1) / (maxx - minx))
        sy = int((y - miny) * (self.screen_height - 1) / (maxy - miny))

        # Clamp to screen bounds
        sx = max(0, min(self.screen_width - 1, sx))
        sy = max(0, min(self.screen_height - 1, sy))

        return sx, sy

    def read_events(self):
        """Generator yielding touch events.

        Yields:
            evdev.InputEvent: Touch events from device
        """
        if self._device is None:
            logger.warning("Touch device not initialized, cannot read events")
            return

        if not EVDEV_AVAILABLE:
            return

        try:
            for event in self._device.read_loop():
                yield event
        except Exception as e:
            logger.error(f"Error reading touch events: {e}")

    def wait_touch_median(self, timeout=8.0, samples=18):
        """Wait for touch and return median-filtered coordinates.

        Args:
            timeout: Maximum time to wait in seconds
            samples: Number of samples to collect for median filter

        Returns:
            tuple: (raw_x, raw_y) median coordinates, or None if timeout
        """
        if self._device is None or not EVDEV_AVAILABLE:
            return None

        t0 = time.time()
        touching = False
        bufx, bufy = [], []

        try:
            for ev in self._device.read_loop():
                if time.time() - t0 > timeout:
                    return None

                if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                    touching = (ev.value == 1)
                    if not touching:
                        bufx.clear()
                        bufy.clear()

                elif ev.type == ecodes.EV_ABS:
                    if ev.code == ecodes.ABS_X:
                        rx = ev.value
                    elif ev.code == ecodes.ABS_Y:
                        ry = ev.value
                    else:
                        continue

                    if touching and 'rx' in locals() and 'ry' in locals():
                        bufx.append(rx)
                        bufy.append(ry)
                        if len(bufx) >= samples:
                            return (int(statistics.median(bufx)), int(statistics.median(bufy)))

                if not touching:
                    time.sleep(0.002)

        except Exception as e:
            logger.error(f"Error during touch wait: {e}")
            return None

        return None

    def set_orientation(self, index):
        """Set orientation configuration.

        Args:
            index: Orientation index (0-7)

        Returns:
            bool: True if valid orientation, False otherwise
        """
        if 0 <= index < len(self.ORIENTATIONS):
            self.orientation_index = index
            logger.info(f"Orientation set to {index + 1}/8")
            return True
        logger.warning(f"Invalid orientation index: {index}")
        return False

    def cycle_orientation(self):
        """Cycle to next orientation configuration.

        Returns:
            int: New orientation index
        """
        self.orientation_index = (self.orientation_index + 1) % len(self.ORIENTATIONS)
        logger.info(f"Orientation cycled to {self.orientation_index + 1}/8")
        return self.orientation_index

    def set_calibration(self, minx, maxx, miny, maxy):
        """Set calibration bounds.

        Args:
            minx: Minimum X value
            maxx: Maximum X value
            miny: Minimum Y value
            maxy: Maximum Y value
        """
        self.calibration = (int(minx), int(maxx), int(miny), int(maxy))
        logger.info(f"Calibration set: X[{minx}..{maxx}] Y[{miny}..{maxy}]")

    def clear_calibration(self):
        """Clear calibration, reverting to driver ranges."""
        self.calibration = None
        logger.info("Calibration cleared")

    def close(self):
        """Close touch device."""
        if self._device:
            try:
                self._device.close()
                logger.info("Touch device closed")
            except Exception as e:
                logger.warning(f"Error closing touch device: {e}")

    @property
    def is_open(self):
        """Check if touch device is open and ready."""
        return self._device is not None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
