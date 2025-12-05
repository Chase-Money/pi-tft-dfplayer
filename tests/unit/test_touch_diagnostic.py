from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.ui.framework.events import UIEvent
from src.ui.framework.manager import ScreenManagerV2
from src.ui.screens.touch_diagnostic import TouchDiagnosticScreen


@pytest.fixture
def screen():
    manager = Mock(spec=ScreenManagerV2)
    manager.pop = Mock()
    app = Mock()
    app.framebuffer = Mock(width=480, height=320)
    app.get_touch_orientation.return_value = {
        "swap_xy": False,
        "flip_x": False,
        "flip_y": False,
    }
    app.get_touch_driver_bounds.return_value = (0, 4095, 0, 4095)

    services = {"app": app}
    diag = TouchDiagnosticScreen(manager, services)
    diag.on_enter()
    return diag


def test_records_tap_with_label_and_history(screen):
    event = UIEvent("tap", {"pos": (10, 10), "raw": (100, 200)})
    assert screen.handle_event(event) is True

    assert screen.tap_history == [("TOP-LEFT", 100, 200, 10, 10, "tap")]
    assert screen.last_tap == (100, 200, 10, 10, "tap", "TOP-LEFT")


def test_drag_events_trim_history(screen):
    for idx in range(screen.HISTORY_LIMIT + 2):
        event = UIEvent("drag", {"pos": (idx, idx), "raw": (idx, idx)})
        screen.handle_event(event)

    assert len(screen.tap_history) == screen.HISTORY_LIMIT
    last_entry = screen.tap_history[-1]
    assert last_entry[-1] == "drag"


def test_identify_corner_respects_framebuffer(screen):
    assert screen._identify_corner(479, 0) == "TOP-RIGHT"
    assert screen._identify_corner(0, 319) == "BOTTOM-LEFT"
