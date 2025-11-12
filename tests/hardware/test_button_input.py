import time

from src.hardware.button_input import ButtonInput, Button, ButtonEvent, _FakeGPIO


def test_press_and_release_polling():
    gpio = _FakeGPIO()
    bi = ButtonInput(gpio=gpio, hold_threshold_ms=300, debounce_ms=20)

    pressed = []
    released = []

    bi.register_callback(Button.KEY1, ButtonEvent.PRESS, lambda: pressed.append("p"))
    bi.register_callback(Button.KEY1, ButtonEvent.RELEASE, lambda: released.append("r"))

    pin = Button.KEY1.value
    # Idle high
    gpio.pin_state[pin] = gpio.HIGH
    bi.poll()

    # Press
    gpio.pin_state[pin] = gpio.LOW
    bi.poll()
    # Short wait, not enough for HOLD
    time.sleep(0.05)
    bi.poll()

    # Release
    gpio.pin_state[pin] = gpio.HIGH
    bi.poll()

    assert pressed == ["p"]
    assert released == ["r"]


def test_hold_suppresses_press():
    gpio = _FakeGPIO()
    bi = ButtonInput(gpio=gpio, hold_threshold_ms=120, debounce_ms=10)

    events = []

    bi.register_callback(Button.KEY2, ButtonEvent.PRESS, lambda: events.append("PRESS"))
    bi.register_callback(Button.KEY2, ButtonEvent.HOLD, lambda: events.append("HOLD"))
    bi.register_callback(Button.KEY2, ButtonEvent.RELEASE, lambda: events.append("RELEASE"))

    pin = Button.KEY2.value
    gpio.pin_state[pin] = gpio.HIGH
    bi.poll()

    # Press and hold beyond threshold
    gpio.pin_state[pin] = gpio.LOW
    t0 = time.time()
    while time.time() - t0 < 0.15:
        bi.poll()
        time.sleep(0.01)

    # Release
    gpio.pin_state[pin] = gpio.HIGH
    bi.poll()

    # We expect PRESS (on down), then HOLD, then RELEASE
    # Policy: HOLD suppresses additional PRESS, but initial PRESS still fires on down edge in poll mode.
    assert events[0] == "PRESS"
    assert "HOLD" in events
    assert events[-1] == "RELEASE"

