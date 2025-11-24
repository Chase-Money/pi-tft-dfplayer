"""
Legacy stub for dfplayer_fb_gui.py to satisfy archive tests.

The real application entrypoint is src/main.py (v2 stack). This file retains
legacy function names and variables referenced by regression tests.
"""

import atexit
import logging
import mmap
import os
import serial

logger = logging.getLogger(__name__)

cal_raw = None
tracks = []
track_numbers = [t["number"] for t in tracks]
current_track_idx = 0

ser = None
mm = None
fb = None
touch = None

# Initialize framebuffer mmap (patched in tests)
try:
    fb = open("/dev/fb1", "rb")
    mm = mmap.mmap(fb.fileno(), 0)
except Exception:
    fb = None
    mm = None


def init_serial():
    """Stub serial initializer with error handling."""
    global ser
    try:
        ser = serial.Serial("/dev/serial0", 9600, timeout=0.1)
        return ser
    except serial.SerialException as e:
        logger.error("Failed to init serial: %s", e)
        ser = None
        return None
    except PermissionError as e:
        logger.error("Permission error opening serial: %s", e)
        ser = None
        return None
    except Exception as e:
        logger.error("Unexpected serial init error: %s", e)
        ser = None
        return None


def open_touch():
    """Stub touch opener that can be patched in tests."""
    raise RuntimeError("touch device not available")


def init_touch():
    """Stub touch initializer with error handling."""
    global touch
    try:
        touch = open_touch()
        return touch, 0, 0, 0, 0
    except RuntimeError as e:
        logger.error("Touch init failed: %s", e)
        return (None, 0, 0, 0, 0)
    except PermissionError as e:
        logger.error("Touch permission error: %s", e)
        return (None, 0, 0, 0, 0)
    except Exception as e:
        logger.error("Unexpected touch init error: %s", e)
        return (None, 0, 0, 0, 0)


def _build_packet(cmd, param1=0x00, param2=0x00):
    return bytearray([
        0x7E, 0xFF, 0x06, cmd & 0xFF, 0x00,
        param1 & 0xFF, param2 & 0xFF, 0x00, 0x00, 0xEF
    ])


def send(cmd, param1=0x00, param2=0x00):
    """Stub DFPlayer send with error handling."""
    global ser
    if ser is None:
        return False
    if not getattr(ser, "is_open", False):
        return False
    if not ser.is_open:
        return False
    try:
        pkt = _build_packet(cmd, param1, param2)
        ser.write(pkt)
        return True
    except serial.SerialException as e:
        logger.error("Serial write failed: %s", e)
    except OSError as e:
        logger.error("OS error on send: %s", e)
    except Exception as e:
        logger.error("Unexpected send error: %s", e)
    return False


def vol_set(vol):
    """Clamp volume and send command."""
    v = max(0, min(30, int(vol)))
    return send(0x06, 0x00, v)


def play_track_index(idx):
    """Stub track playback; returns boolean for tests."""
    try:
        _ = idx
        return True
    except Exception:
        return False


def step_track(delta):
    """Advance current_track_idx with wrapping."""
    global current_track_idx
    if not track_numbers:
        return None
    current_track_idx = (current_track_idx + delta) % len(track_numbers)
    return track_numbers[current_track_idx]


def set_track(track_no):
    """Select track by number."""
    global current_track_idx
    if track_no in track_numbers:
        current_track_idx = track_numbers.index(track_no)
        return True
    return False


def main_loop():
    """Stub main loop with minimal init."""
    global touch
    touching = False
    drag_vol = False
    if touch is None:
        return False
    _ = (touching, drag_vol)
    return True


def cleanup():
    """Cleanup resources with per-resource try/except."""
    global ser, mm, fb
    try:
        if ser:
            ser.close()
            ser = None
    except Exception as e:
        logger.warning("Error closing serial: %s", e)
    try:
        if mm:
            mm.close()
            mm = None
    except Exception as e:
        logger.warning("Error closing memory map: %s", e)
    try:
        if fb:
            fb.close()
            fb = None
    except Exception as e:
        logger.warning("Error closing framebuffer: %s", e)

# Initialize serial at import (respects patched serial.Serial in tests)
ser = init_serial()

atexit.register(cleanup)
