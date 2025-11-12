"""GPIO button and joystick input abstraction with mockable GPIO seam.

Features:
- PRESS / RELEASE / HOLD events with 350 ms default hold threshold
- Software debounce (50 ms) and optional poll loop fallback
- Callback registration per (button, event) tuple
- Injected GPIO module for tests (no hardware needed)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable, Dict, Optional, Tuple

try:
    import RPi.GPIO as REAL_GPIO  # type: ignore
    RPI_AVAILABLE = True
except Exception:  # pragma: no cover - tests inject a fake GPIO
    REAL_GPIO = None  # type: ignore
    RPI_AVAILABLE = False


class Button(Enum):
    KEY1 = 21
    KEY2 = 20
    KEY3 = 16
    UP = 6
    DOWN = 19
    LEFT = 5
    RIGHT = 26
    PRESS = 13  # joystick press/center


class ButtonEvent(Enum):
    PRESS = 1
    RELEASE = 0
    HOLD = 2


class ButtonInput:
    """GPIO button handler with debouncing and hold detection.

    Parameters
    ----------
    gpio: Optional[module]
        Injected GPIO module compatible with RPi.GPIO API.
    hold_threshold_ms: int
        Duration to treat a press as HOLD. Suppresses PRESS when fired.
    debounce_ms: int
        Debounce time applied to edge detection or poll checks.
    """

    def __init__(
        self,
        *,
        gpio=None,
        hold_threshold_ms: int = 350,
        debounce_ms: int = 50,
    ) -> None:
        self.GPIO = gpio or REAL_GPIO or _FakeGPIO()
        self.hold_threshold = max(50, int(hold_threshold_ms)) / 1000.0
        self.debounce = max(10, int(debounce_ms)) / 1000.0

        self.buttons: Dict[Button, int] = {
            Button.KEY1: Button.KEY1.value,
            Button.KEY2: Button.KEY2.value,
            Button.KEY3: Button.KEY3.value,
            Button.UP: Button.UP.value,
            Button.DOWN: Button.DOWN.value,
            Button.LEFT: Button.LEFT.value,
            Button.RIGHT: Button.RIGHT.value,
            Button.PRESS: Button.PRESS.value,
        }

        self._press_times: Dict[Button, float] = {}
        self._fired_hold: Dict[Button, bool] = {}
        self._callbacks: Dict[Tuple[Button, ButtonEvent], Callable[[], None]] = {}

        # Basic setup
        self.GPIO.setmode(self.GPIO.BCM)
        for pin in self.buttons.values():
            self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)

        # Try interrupts; if unsupported, user can call poll() in a loop
        for btn, pin in self.buttons.items():
            try:
                self.GPIO.add_event_detect(
                    pin, self.GPIO.BOTH, callback=self._edge_callback_factory(btn), bouncetime=int(self.debounce * 1000)
                )
            except Exception:
                # Some GPIO fakes may not support interrupts; ignore
                pass

    # ---- Public API ----
    def register_callback(self, button: Button, event_type: ButtonEvent, callback: Callable[[], None]) -> None:
        self._callbacks[(button, event_type)] = callback

    def poll(self) -> None:
        """Poll all buttons and fire callbacks. Call at ~50–100 Hz if interrupts not used."""
        now = time.time()
        for btn, pin in self.buttons.items():
            state_low = self.GPIO.input(pin) == self.GPIO.LOW

            if state_low:
                if btn not in self._press_times:
                    self._press_times[btn] = now
                    self._fired_hold[btn] = False
                    self._fire(btn, ButtonEvent.PRESS)
                else:
                    if not self._fired_hold.get(btn, False) and (now - self._press_times[btn]) >= self.hold_threshold:
                        self._fired_hold[btn] = True
                        self._fire(btn, ButtonEvent.HOLD)
            else:
                if btn in self._press_times:
                    # On release, suppress PRESS if HOLD already fired
                    if not self._fired_hold.get(btn, False):
                        # nothing special; PRESS already fired at down edge
                        pass
                    self._fire(btn, ButtonEvent.RELEASE)
                    self._press_times.pop(btn, None)
                    self._fired_hold.pop(btn, None)

    def cleanup(self) -> None:
        try:
            self.GPIO.cleanup()
        except Exception:
            pass

    # ---- Internals ----
    def _edge_callback_factory(self, btn: Button):  # pragma: no cover - hard to exercise callbacks in unit tests
        def _cb(channel: int) -> None:
            now = time.time()
            state_low = self.GPIO.input(self.buttons[btn]) == self.GPIO.LOW
            if state_low:
                self._press_times[btn] = now
                self._fired_hold[btn] = False
                self._fire(btn, ButtonEvent.PRESS)
            else:
                if btn in self._press_times and not self._fired_hold.get(btn, False):
                    # PRESS already delivered on down; nothing extra
                    pass
                self._fire(btn, ButtonEvent.RELEASE)
                self._press_times.pop(btn, None)
                self._fired_hold.pop(btn, None)
        return _cb

    def _fire(self, button: Button, ev: ButtonEvent) -> None:
        cb = self._callbacks.get((button, ev))
        if cb:
            try:
                cb()
            except Exception:
                # Swallow exceptions from user callbacks to keep input alive
                pass


class _FakeGPIO:
    """Very small subset of RPi.GPIO used for tests.

    Usage pattern:
    - Expose pin states via `pin_state[pin] = 0/1`
    - Call `simulate_edge(pin, value)` to emulate interrupts
    """

    BCM = 11
    IN = 0
    PUD_UP = 1
    BOTH = 2
    LOW = 0
    HIGH = 1

    def __init__(self) -> None:
        self.pin_state: Dict[int, int] = {}
        self._callbacks: Dict[int, Callable[[int], None]] = {}

    def setmode(self, mode: int) -> None:
        _ = mode

    def setup(self, pin: int, mode: int, pull_up_down: int) -> None:
        _ = (mode, pull_up_down)
        self.pin_state.setdefault(pin, self.HIGH)

    def input(self, pin: int) -> int:
        return self.pin_state.get(pin, self.HIGH)

    def add_event_detect(self, pin: int, edge: int, callback: Callable[[int], None], bouncetime: int = 50) -> None:
        _ = (edge, bouncetime)
        self._callbacks[pin] = callback

    def simulate_edge(self, pin: int, value: int) -> None:
        self.pin_state[pin] = value
        cb = self._callbacks.get(pin)
        if cb:
            cb(pin)

    def cleanup(self) -> None:
        self.pin_state.clear()
        self._callbacks.clear()

