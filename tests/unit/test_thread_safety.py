"""Thread safety tests for DFPlayerBackend.

Tests concurrent access to backend state, event queues, and listener thread operations
to ensure thread-safe behavior without data corruption or race conditions.
"""

import queue
import threading
import time
import pytest
from typing import List
from unittest.mock import Mock, patch

from src.backends.dfplayer import DFPlayerBackend


class FakeDFPlayerForThreading:
    """Mock DFPlayer with thread-safe response queue."""

    def __init__(self, connected: bool = True):
        self.is_connected = connected
        self.responses = queue.Queue()
        self.call_count_lock = threading.Lock()
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0
        self.volume_calls = []
        self.play_track_calls = []
        self.closed = False

    def set_volume(self, volume: int):
        with self.call_count_lock:
            self.volume_calls.append(volume)

    def play(self):
        with self.call_count_lock:
            self.play_calls += 1

    def pause(self):
        with self.call_count_lock:
            self.pause_calls += 1

    def stop(self):
        with self.call_count_lock:
            self.stop_calls += 1

    def next_track(self):
        pass

    def prev_track(self):
        pass

    def play_track(self, number: int):
        with self.call_count_lock:
            self.play_track_calls.append(number)

    def read_response(self, timeout: float = 0.1):
        try:
            return self.responses.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        self.closed = True


def _build_packet(cmd: int, p1: int = 0, p2: int = 0) -> bytes:
    """Build DFPlayer protocol packet."""
    pkt = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, p1, p2, 0x00, 0x00, 0xEF])
    total = sum(pkt[1:7]) & 0xFFFF
    cs = (0xFFFF - total + 1) & 0xFFFF
    pkt[7], pkt[8] = (cs >> 8) & 0xFF, cs & 0xFF
    return bytes(pkt)


class TestConcurrentStateAccess:
    """Test concurrent access to backend state variables."""

    def test_concurrent_volume_changes(self, monkeypatch):
        """Test multiple threads calling set_volume simultaneously."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        # Spawn multiple threads to set volume concurrently
        num_threads = 20
        volumes_per_thread = 10
        threads: List[threading.Thread] = []

        def set_volumes(thread_id: int):
            for i in range(volumes_per_thread):
                volume = (thread_id + i) % 31  # 0-30 range
                backend.set_volume(volume)
                time.sleep(0.001)  # Small delay to increase interleaving

        for i in range(num_threads):
            t = threading.Thread(target=set_volumes, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Verify all volume calls were received
        expected_total = num_threads * volumes_per_thread
        assert len(fake.volume_calls) == expected_total, \
            f"Expected {expected_total} volume calls, got {len(fake.volume_calls)}"

        # Verify final state is consistent (last volume set)
        assert backend.volume_level is not None
        assert 0 <= backend.volume_level <= 30

        backend.shutdown()

    def test_concurrent_play_pause_operations(self, monkeypatch):
        """Test concurrent play/pause/stop operations."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        # Spawn threads to call play, pause, stop concurrently
        num_threads = 15
        operations = []

        def play_operations():
            for _ in range(5):
                backend.play()
                time.sleep(0.001)
            operations.append("play")

        def pause_operations():
            for _ in range(5):
                backend.pause()
                time.sleep(0.001)
            operations.append("pause")

        def stop_operations():
            for _ in range(5):
                backend.stop()
                time.sleep(0.001)
            operations.append("stop")

        threads = []
        for i in range(num_threads):
            if i % 3 == 0:
                t = threading.Thread(target=play_operations)
            elif i % 3 == 1:
                t = threading.Thread(target=pause_operations)
            else:
                t = threading.Thread(target=stop_operations)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Verify counts match expected
        assert fake.play_calls >= 5
        assert fake.pause_calls >= 5
        assert fake.stop_calls >= 5

        # Verify state is consistent (bool values only)
        assert isinstance(backend.playing, bool)
        assert isinstance(backend.play_pending, bool)

        backend.shutdown()

    def test_concurrent_track_playback(self, monkeypatch):
        """Test concurrent play_track calls with different track numbers."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        num_threads = 10
        threads = []

        def play_track_sequence(start_track: int):
            for i in range(5):
                backend.play_track(start_track + i)
                time.sleep(0.001)

        for i in range(num_threads):
            t = threading.Thread(target=play_track_sequence, args=(i * 10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Verify all track calls were made
        expected_total = num_threads * 5
        assert len(fake.play_track_calls) == expected_total

        # Verify no duplicate tracks in calls (each thread plays unique tracks)
        # Note: Current implementation doesn't prevent duplicate track calls,
        # we just verify the count matches expected
        assert backend.play_pending is not None  # State should exist

        backend.shutdown()

    def test_concurrent_status_reads(self, monkeypatch):
        """Test concurrent get_status calls while state is changing."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        statuses = []
        status_lock = threading.Lock()

        def read_status():
            for _ in range(20):
                status = backend.get_status()
                with status_lock:
                    statuses.append(status)
                time.sleep(0.001)

        def change_state():
            for i in range(10):
                backend.set_volume(i % 31)
                backend.play()
                backend.pause()
                time.sleep(0.002)

        threads = []
        # Multiple readers
        for _ in range(5):
            t = threading.Thread(target=read_status)
            threads.append(t)
            t.start()

        # One writer
        t = threading.Thread(target=change_state)
        threads.append(t)
        t.start()

        for t in threads:
            t.join(timeout=10.0)

        # Verify all status reads completed successfully
        assert len(statuses) >= 100  # 5 threads * 20 reads

        # Verify all status dictionaries have required keys
        for status in statuses:
            assert "playing" in status
            assert "volume" in status
            assert "connected" in status
            assert isinstance(status["playing"], bool)
            assert isinstance(status["volume"], int)

        backend.shutdown()


class TestEventQueueRaceConditions:
    """Test event queue operations under concurrent access."""

    def test_event_queue_full_handling(self, monkeypatch):
        """Test event queue full condition with concurrent listener updates."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        # Fill queue beyond capacity to trigger drop behavior
        for i in range(backend.EVENT_QUEUE_SIZE + 50):
            try:
                backend._event_queue.put({"type": "test", "index": i}, block=False)
            except queue.Full:
                pass

        # Verify queue has events but not more than max
        queue_size = backend._event_queue.qsize()
        assert queue_size <= backend.EVENT_QUEUE_SIZE

        backend.shutdown()

    def test_concurrent_event_polling(self, monkeypatch):
        """Test multiple threads polling events simultaneously."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        # Pre-populate queue with events
        num_events = 50
        for i in range(num_events):
            backend._event_queue.put({"type": "test", "index": i})

        polled_events = []
        events_lock = threading.Lock()

        def poll_events():
            for _ in range(20):
                event = backend.poll_event(timeout=0.01)
                if event:
                    with events_lock:
                        polled_events.append(event)
                time.sleep(0.001)

        num_threads = 5
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=poll_events)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        # Verify events were polled (some may timeout, so check >= some threshold)
        assert len(polled_events) > 0

        # Verify no duplicate events (each event should be polled once)
        indices = [e.get("index") for e in polled_events if e.get("index") is not None]
        assert len(indices) == len(set(indices)), "Duplicate events detected"

        backend.shutdown()

    def test_listener_event_generation_with_concurrent_polling(self, monkeypatch):
        """Test listener thread generating events while consumer threads poll."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)

        # Don't suppress listener thread for this test - we want to test concurrency
        backend.initialize()

        # Queue responses for listener to process
        for i in range(20):
            fake.responses.put(_build_packet(0x3D))  # Track finished
            fake.responses.put(_build_packet(0x3E, 0x00, i + 1))  # Track started

        polled_events = []
        events_lock = threading.Lock()
        stop_polling = threading.Event()

        def poll_continuously():
            while not stop_polling.is_set():
                event = backend.poll_event(timeout=0.05)
                if event:
                    with events_lock:
                        polled_events.append(event)

        # Start multiple consumer threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=poll_continuously)
            threads.append(t)
            t.start()

        # Let listener and consumers run
        time.sleep(1.0)

        # Stop polling
        stop_polling.set()
        for t in threads:
            t.join(timeout=5.0)

        # Verify events were generated and consumed
        assert len(polled_events) > 0

        # Verify event types are correct
        event_types = [e.get("type") for e in polled_events]
        assert "track_finished" in event_types or "track_started" in event_types

        backend.shutdown()


class TestListenerThreadShutdown:
    """Test listener thread lifecycle and shutdown scenarios."""

    def test_shutdown_during_active_listening(self):
        """Test shutdown while listener thread is actively processing."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        # Queue many responses to keep listener busy
        for i in range(100):
            fake.responses.put(_build_packet(0x3E, 0x00, i))

        # Give listener time to start processing
        time.sleep(0.1)

        # Shutdown should cleanly stop listener
        backend.shutdown()

        # Verify clean shutdown
        assert backend.device is None
        assert backend.playing is False
        assert backend._listener_thread is None or not backend._listener_thread.is_alive()

    def test_shutdown_with_empty_queue(self):
        """Test shutdown when event queue is empty."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        # No events queued
        time.sleep(0.1)

        # Shutdown
        backend.shutdown()

        # Verify clean shutdown
        assert backend.device is None
        assert backend._stop_event.is_set()

    def test_shutdown_with_full_queue(self, monkeypatch):
        """Test shutdown when event queue is full."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        # Fill event queue
        for i in range(backend.EVENT_QUEUE_SIZE):
            try:
                backend._event_queue.put({"type": "test", "index": i}, block=False)
            except queue.Full:
                break

        # Verify queue is full
        assert backend._event_queue.full()

        # Shutdown should succeed even with full queue
        backend.shutdown()

        assert backend.device is None

    def test_concurrent_shutdown_calls(self):
        """Test multiple threads calling shutdown simultaneously."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        shutdown_results = []
        results_lock = threading.Lock()

        def call_shutdown():
            try:
                backend.shutdown()
                with results_lock:
                    shutdown_results.append("success")
            except Exception as e:
                with results_lock:
                    shutdown_results.append(f"error: {e}")

        # Spawn multiple threads to call shutdown
        threads = []
        for _ in range(5):
            t = threading.Thread(target=call_shutdown)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # All shutdowns should complete without error
        assert len(shutdown_results) == 5
        assert all(r == "success" for r in shutdown_results)

        # Verify final state
        assert backend.device is None

    def test_operations_during_shutdown(self, monkeypatch):
        """Test calling playback operations during shutdown."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        shutdown_started = threading.Event()
        operation_errors = []
        errors_lock = threading.Lock()

        def slow_shutdown():
            """Shutdown with artificial delay."""
            shutdown_started.set()
            time.sleep(0.1)
            backend._stop_listener()
            with backend._device_lock:
                if backend.device:
                    backend.device.close()
                backend.device = None

        def attempt_operations():
            shutdown_started.wait(timeout=1.0)
            # Try operations during shutdown
            try:
                backend.play()
            except Exception as e:
                with errors_lock:
                    operation_errors.append(("play", str(e)))

            try:
                backend.set_volume(15)
            except Exception as e:
                with errors_lock:
                    operation_errors.append(("set_volume", str(e)))

        t1 = threading.Thread(target=slow_shutdown)
        t2 = threading.Thread(target=attempt_operations)

        t1.start()
        t2.start()

        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        # Operations might fail or succeed depending on timing
        # The important thing is no crashes or deadlocks occurred
        assert backend.device is None


class TestStateLockConsistency:
    """Test state lock prevents inconsistent state updates."""

    def test_play_pause_state_consistency(self, monkeypatch):
        """Test play/pause state changes are atomic."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        monkeypatch.setattr(backend, "_start_listener", lambda: None)
        backend.initialize()

        state_snapshots = []
        snapshots_lock = threading.Lock()

        def capture_states():
            for _ in range(100):
                with backend._state_lock:
                    snapshot = (backend.playing, backend.play_pending)
                with snapshots_lock:
                    state_snapshots.append(snapshot)
                time.sleep(0.001)

        def toggle_playback():
            for _ in range(50):
                backend.play()
                time.sleep(0.001)
                backend.pause()
                time.sleep(0.001)

        t1 = threading.Thread(target=capture_states)
        t2 = threading.Thread(target=toggle_playback)

        t1.start()
        t2.start()

        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        # Verify all snapshots have valid boolean values
        for playing, pending in state_snapshots:
            assert isinstance(playing, bool)
            assert isinstance(pending, bool)

        backend.shutdown()

    def test_track_number_consistency(self, monkeypatch):
        """Test current_track updates are consistent."""
        fake = FakeDFPlayerForThreading()
        backend = DFPlayerBackend(port="/dev/null", dfplayer_factory=lambda p, b: fake)
        backend.initialize()

        # Queue track_started events
        for i in range(20):
            fake.responses.put(_build_packet(0x3E, 0x00, i + 1))

        track_snapshots = []
        snapshots_lock = threading.Lock()

        def capture_tracks():
            for _ in range(50):
                status = backend.get_status()
                with snapshots_lock:
                    track_snapshots.append(status["track_number"])
                time.sleep(0.01)

        t = threading.Thread(target=capture_tracks)
        t.start()

        # Let listener process events
        time.sleep(0.3)

        t.join(timeout=5.0)

        # Verify track numbers are either None or valid integers
        for track in track_snapshots:
            assert track is None or isinstance(track, int)

        backend.shutdown()
