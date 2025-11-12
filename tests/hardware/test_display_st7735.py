import os
import types

import pytest


def test_emulator_device_push_and_clear_without_pil(monkeypatch):
    # Force emulator mode regardless of luma presence
    monkeypatch.setenv("DFPLAYER_USE_EMULATOR", "1")

    # Lazy import to respect env var
    from src.hardware.display_st7735 import DisplayST7735

    disp = DisplayST7735()

    # Push a plain object without PIL available
    class Dummy:
        def __init__(self):
            self.size = (64, 64)

    dummy = Dummy()
    disp.push(dummy)

    # Clear should not crash without PIL
    disp.clear((1, 2, 3))

    # Close is a no-op in emulator
    disp.close()


def test_injected_device_receives_display_calls(monkeypatch):
    from src.hardware.display_st7735 import DisplayST7735

    calls = {"n": 0}

    class FakeDev:
        def __init__(self):
            self.frames = []

        def display(self, frame):
            calls["n"] += 1
            self.frames.append(frame)

        def cleanup(self):
            pass

    dev = FakeDev()
    disp = DisplayST7735(device=dev)
    disp.push({"frame": 1})
    disp.push({"frame": 2})
    disp.clear((0, 0, 0))
    assert calls["n"] >= 2

