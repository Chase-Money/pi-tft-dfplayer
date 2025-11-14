"""ST7735S display abstraction with mockable seams and emulator fallback.

This module provides a small, testable wrapper around luma.lcd's ST7735 device.
It supports:
- Optional emulator device when luma.lcd or SPI hardware is not available
- Basic API: push(image_like), clear(color), close()
- Optional backlight PWM controls: set_brightness(), fade_to()

Design goals:
- Zero hard dependency on luma.lcd for unit tests
- Narrow, well-documented public surface area
- Fail fast with helpful errors on misconfiguration
"""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple, Any

try:
    from PIL import Image  # type: ignore
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - environment may not have Pillow
    Image = None  # type: ignore
    PIL_AVAILABLE = False

try:  # Optional dependency: luma.lcd
    from luma.core.interface.serial import spi  # type: ignore
    from luma.lcd.device import st7735  # type: ignore
    LUMA_AVAILABLE = True
except Exception:  # pragma: no cover - not required for tests
    spi = None  # type: ignore
    st7735 = None  # type: ignore
    LUMA_AVAILABLE = False

try:  # Optional dependency: RPi.GPIO for backlight PWM
    import RPi.GPIO as RPI_GPIO  # type: ignore
    RPI_AVAILABLE = True
except Exception:  # pragma: no cover - not required for tests
    RPI_GPIO = None  # type: ignore
    RPI_AVAILABLE = False


class _EmulatorDevice:
    """Very small emulator that records last frame and counts displays.

    Intended for tests and development without hardware. If PIL is available,
    it accepts PIL Images; otherwise any object with a `.size` attribute is
    tolerated for basic shape checks.
    """

    def __init__(self, width: int = 128, height: int = 128):
        self.width = width
        self.height = height
        self.display_calls = 0
        self.last_frame: Optional[Any] = None

    def display(self, img_like: Any) -> None:
        self.display_calls += 1
        self.last_frame = img_like

    def cleanup(self) -> None:
        self.last_frame = None


class DisplayST7735:
    """ST7735S display abstraction using luma.lcd or an emulator.

    Parameters
    ----------
    use_emulator: bool
        Force using the emulator regardless of luma availability. Useful for
        tests and development on machines without SPI hardware.
    rotation: int
        Rotation passed to luma.lcd device. Common values 0/90/180/270.
    bgr: bool
        Whether the panel uses BGR color order. Waveshare 1.44" typically does.
    backlight_pin: Optional[int]
        GPIO pin for backlight PWM (BCM numbering). If provided and RPi.GPIO is
        available, enables brightness control.
    """

    def __init__(
        self,
        *,
        use_emulator: Optional[bool] = None,
        rotation: int = 0,
        bgr: bool = True,
        backlight_pin: Optional[int] = 24,
        device: Optional[Any] = None,  # for dependency injection (tests)
    ) -> None:
        self.width = 128
        self.height = 128
        self._device = None
        self._pwm = None
        self._backlight_pin = backlight_pin

        # Decide emulator vs hardware
        if use_emulator is None:
            # Allow environment override; default to emulator if luma missing
            env = os.environ.get("DFPLAYER_USE_EMULATOR", "0").strip()
            use_emulator = (env == "1") or not LUMA_AVAILABLE

        if device is not None:
            # Injected device for tests
            self._device = device
        elif use_emulator:
            self._device = _EmulatorDevice(self.width, self.height)
        else:
            # Initialize luma.lcd
            assert LUMA_AVAILABLE, "luma.lcd not available"
            assert spi is not None and st7735 is not None
            serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
            self._device = st7735(serial, width=self.width, height=self.height, rotate=rotation, bgr=bgr)

        # Optional backlight PWM
        if self._backlight_pin is not None and RPI_AVAILABLE:
            try:  # pragma: no cover - cannot exercise PWM in unit tests
                RPI_GPIO.setmode(RPI_GPIO.BCM)
                RPI_GPIO.setup(self._backlight_pin, RPI_GPIO.OUT)
                self._pwm = RPI_GPIO.PWM(self._backlight_pin, 1000)  # 1 kHz
                self._pwm.start(100)  # full brightness
            except Exception:
                self._pwm = None

    def push(self, img_like: Any) -> None:
        """Display a frame.

        If PIL is available and `img_like` is an Image in any mode/size, it
        will be converted to RGB and resized to 128×128. Otherwise, the object
        is passed through to the device as-is.
        """
        if PIL_AVAILABLE and Image is not None and isinstance(img_like, Image.Image):
            img = img_like
            if getattr(img, "mode", None) != "RGB":  # type: ignore
                img = img.convert("RGB")  # type: ignore
            if img.size != (self.width, self.height):  # type: ignore
                img = img.resize((self.width, self.height))  # type: ignore
            self._device.display(img)
        else:
            # Best-effort pass-through for tests without PIL
            self._device.display(img_like)

    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        if PIL_AVAILABLE and Image is not None:
            img = Image.new("RGB", (self.width, self.height), color)
            self.push(img)
        else:
            # No PIL: push a simple token
            self.push({"clear": color, "size": (self.width, self.height)})

    def set_brightness(self, percent: int) -> None:
        """Set backlight brightness via PWM if available (0–100)."""
        percent = max(0, min(100, int(percent)))
        if self._pwm is not None:  # pragma: no cover - hardware only
            self._pwm.ChangeDutyCycle(percent)

    def fade_to(self, percent: int, ms: int = 250) -> None:
        """Fade backlight to target brightness over ms (hardware only)."""
        if self._pwm is None:  # pragma: no cover - hardware only
            return
        percent = max(0, min(100, int(percent)))
        # Crude linear fade
        # Read current duty cycle is not trivial; sweep instead
        steps = max(1, ms // 15)
        # Assume start at 0 or 100 based on heuristic
        start = 0
        for duty in _lerp(start, percent, steps):
            self._pwm.ChangeDutyCycle(duty)
            time.sleep(ms / max(1, steps) / 1000.0)

    def close(self) -> None:
        if hasattr(self._device, "cleanup"):
            try:
                self._device.cleanup()
            except Exception:
                pass
        if self._pwm is not None:  # pragma: no cover - hardware only
            try:
                self._pwm.stop()
            except Exception:
                pass


def _lerp(start: int, end: int, steps: int):
    if steps <= 1:
        yield end
        return
    delta = (end - start) / float(steps)
    for i in range(steps):
        yield int(round(start + delta * i))
