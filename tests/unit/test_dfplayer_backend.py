"""
Updated tests for DFPlayer backend to validate delegation to hardware DFPlayer
and async event handling without exercising low-level serial packet logic.
"""

import queue
import pytest

from src.backends.dfplayer import DFPlayerBackend


class FakeDFPlayer:
    def __init__(self, connected: bool = True):
        self.is_connected = connected
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0
        self.next_calls = 0
        self.prev_calls = 0
        self.play_track_calls = []
        self.last_volume = None
        self.closed = False
        self.responses = queue.Queue()

    def set_volume(self, volume: int):
        self.last_volume = volume

    def play(self):
        self.play_calls += 1

    def pause(self):
        self.pause_calls += 1

    def stop(self):
        self.stop_calls += 1

    def next_track(self):
        self.next_calls += 1

    def prev_track(self):
        self.prev_calls += 1

    def play_track(self, number: int):
        self.play_track_calls.append(number)

    def read_response(self, timeout: float = 0.1):
        try:
            return self.responses.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self.closed = True


def _build_packet(cmd: int, p1: int = 0, p2: int = 0) -> bytes:
    pkt = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, p1, p2, 0x00, 0x00, 0xEF])
    total = sum(pkt[1:7]) & 0xFFFF
    cs = (0xFFFF - total + 1) & 0xFFFF
    pkt[7], pkt[8] = (cs >> 8) & 0xFF, cs & 0xFF
    return bytes(pkt)


@pytest.fixture
def fake_dfplayer():
    return FakeDFPlayer()


@pytest.fixture
def backend(fake_dfplayer, monkeypatch):
    backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake_dfplayer)
    # Avoid spawning listener threads in unit tests
    monkeypatch.setattr(backend, "_start_listener", lambda: None)
    backend.initialize()
    return backend, fake_dfplayer


def test_initialize_success_sets_volume(backend):
    backend_instance, device = backend
    assert backend_instance.device is device
    assert device.last_volume == backend_instance.volume_level


def test_initialize_fails_when_not_connected(monkeypatch):
    fake = FakeDFPlayer(connected=False)
    backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
    monkeypatch.setattr(backend, "_start_listener", lambda: None)
    ok = backend.initialize()
    assert ok is False
    assert backend.device is None


def test_set_volume_clamps_and_delegates(backend):
    backend_instance, device = backend
    backend_instance.set_volume(99)
    assert backend_instance.volume_level == 30
    assert device.last_volume == 30
    backend_instance.set_volume(-5)
    assert backend_instance.volume_level == 0
    assert device.last_volume == 0


def test_playback_controls_delegate_to_device(backend):
    backend_instance, device = backend
    backend_instance.play()
    backend_instance.pause()
    backend_instance.stop()
    backend_instance.next_track()
    backend_instance.prev_track()
    backend_instance.play_track(7)

    assert device.play_calls == 1
    assert device.pause_calls == 1
    assert device.stop_calls == 1
    assert device.next_calls == 1
    assert device.prev_calls == 1
    assert device.play_track_calls == [7]
    # Track will be confirmed by 0x3E event; before that we only expect pending state
    assert backend_instance.current_track is None
    assert backend_instance.play_pending is True


def test_poll_event_returns_enqueued_events(backend):
    backend_instance, _ = backend
    evt = {"type": "track_finished"}
    backend_instance._event_queue.put(evt)
    assert backend_instance.poll_event(timeout=0) == evt
    assert backend_instance.poll_event(timeout=0) is None


def test_listener_loop_enqueues_track_and_error_events(fake_dfplayer):
    backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake_dfplayer)
    backend._start_listener = lambda: None
    backend.initialize()

    # Track finished packet
    def _read_response_track_finished(timeout=0.1):
        backend._listener_running = False
        return _build_packet(0x3D, 0x00, 0x00)

    fake_dfplayer.read_response = _read_response_track_finished
    backend._listener_running = True
    backend._listener_loop()
    evt = backend.poll_event(timeout=0)
    assert evt == {"type": "track_finished"}

    # Track started packet
    def _read_response_track_started(timeout=0.1):
        backend._listener_running = False
        return _build_packet(0x3E, 0x00, 0x05)

    fake_dfplayer.read_response = _read_response_track_started
    backend._listener_running = True
    backend._listener_loop()
    evt = backend.poll_event(timeout=0)
    assert evt == {"type": "track_started", "track": 5}

    # Error packet
    def _read_response_error(timeout=0.1):
        backend._listener_running = False
        return _build_packet(0x40, 0x00, 0x10)

    fake_dfplayer.read_response = _read_response_error
    backend._listener_running = True
    backend._listener_loop()
    evt = backend.poll_event(timeout=0)
    assert evt == {"type": "error", "code": 0x10}


def test_shutdown_and_cleanup_close_device(backend):
    backend_instance, device = backend
    backend_instance.shutdown()
    assert device.stop_calls == 1
    assert device.closed is True
    assert backend_instance.device is None
    assert backend_instance.playing is False

    # cleanup should be safe to call after shutdown
    backend_instance.cleanup()
