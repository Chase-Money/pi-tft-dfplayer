from src.ui.framework.manager import ScreenManagerV2, ScreenView
from src.ui.framework.events import UIEvent


class DummyScreen(ScreenView):
    name = "dummy"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.events = []

    def handle_event(self, event):
        self.events.append(event.type)
        return True


def test_screen_manager_push_pop():
    mgr = ScreenManagerV2()
    mgr.register("dummy", DummyScreen)
    mgr.push("dummy")
    assert mgr.stack() == ["dummy"]
    mgr.pop()
    assert mgr.stack() == []


def test_screen_manager_replace():
    class ScreenA(DummyScreen):
        name = "A"

    class ScreenB(DummyScreen):
        name = "B"

    mgr = ScreenManagerV2()
    mgr.register("A", ScreenA)
    mgr.register("B", ScreenB)
    mgr.push("A")
    mgr.replace("B")
    assert mgr.stack() == ["B"]


def test_screen_manager_events_routed():
    mgr = ScreenManagerV2()
    mgr.register("dummy", DummyScreen)
    screen = mgr.push("dummy")
    event = UIEvent("tap", {"pos": (10, 10)})
    handled = mgr.handle_event(event)
    assert handled
    assert screen.events == ["tap"]
