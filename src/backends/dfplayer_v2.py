"""DFPlayer backend for the v2 UI framework."""

import logging
import queue
import threading
from typing import Any, Dict, Optional, Callable

from backends.base import PlaybackBackend
from hardware.dfplayer import DFPlayer
from backends.robust_serial import RobustSerial

logger = logging.getLogger(__name__)


class DFPlayerBackend(PlaybackBackend):
    """Playback backend that wraps the hardware DFPlayer interface."""

    def __init__(self, port: str = '/dev/serial0', baudrate: int = 9600,
                 dfplayer_factory: Optional[Callable[[str, int], DFPlayer]] = None):
        super().__init__(name="DFPlayer")
        self.port = port
        self.baudrate = baudrate
        self._dfplayer_factory = dfplayer_factory or (lambda p, b: DFPlayer(p, b))
        self.device: Optional[DFPlayer] = None
        self.current_track: Optional[int] = None
        self.volume_level: int = 18
        self.playing: bool = False
        self.play_pending: bool = False
        self._state_lock = threading.Lock()  # Protect playing/play_pending state
        self._device_lock = threading.Lock()  # Protect device access during shutdown
        self._event_queue: queue.Queue = queue.Queue(maxsize=100)  # Prevent unbounded growth
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()  # Signal listener thread to stop
        self._dropped_events = 0  # Track dropped events for monitoring
        self._dropped_events_lock = threading.Lock()  # Protect counter access

    # Lifecycle -----------------------------------------------------
    def initialize(self) -> bool:
        try:
            serial_conn = RobustSerial(self.port, self.baudrate, timeout=0.1)
            # Create and configure device before assigning to self.device
            device = self._dfplayer_factory(self.port, self.baudrate)
            if hasattr(device, "serial"):
                device.serial = serial_conn
            self._serial = serial_conn

            # Validate device was created successfully
            if device is None:
                logger.error("DFPlayer factory returned None")
                return False

            if not getattr(device, "is_connected", False):
                logger.error("DFPlayer not connected")
                return False

            device.set_volume(self.volume_level)

            # Assign to self.device under lock before starting listener thread
            with self._device_lock:
                self.device = device

            self._start_listener()
            logger.info("DFPlayer backend initialized successfully")
            return True
        except Exception as exc:
            logger.error(f"Failed to initialize DFPlayer backend: {exc}")
            with self._device_lock:
                self.device = None
            return False

    def shutdown(self):
        self._stop_listener()
        with self._device_lock:
            if self.device:
                try:
                    self.device.stop()
                    self.device.close()
                except Exception as exc:
                    logger.error(f"Error during DFPlayer shutdown: {exc}")
            self.device = None
        with self._state_lock:
            self.playing = False
            self.play_pending = False
            self.current_track = None

    def cleanup(self):
        """Alias for shutdown for backward compatibility."""
        self.shutdown()

    # Controls ------------------------------------------------------
    def play(self):
        if self.device and self.device.is_connected:
            try:
                with self._state_lock:
                    self.play_pending = True
                self.device.play()
            except Exception as exc:
                with self._state_lock:
                    self.playing = False  # Ensure consistent state on failure
                    self.play_pending = False
                logger.error(f"Failed to play: {exc}")
                raise

    def resume(self):
        """Alias for play() to match existing UI expectations."""
        self.play()

    def pause(self):
        if self.device and self.device.is_connected:
            try:
                self.device.pause()
                with self._state_lock:
                    self.playing = False
                    self.play_pending = False
            except Exception as exc:
                # State already False, no need to reset
                logger.error(f"Failed to pause: {exc}")
                raise

    def stop(self):
        if self.device and self.device.is_connected:
            try:
                self.device.stop()
                with self._state_lock:
                    self.playing = False
                    self.play_pending = False
                    self.current_track = None
            except Exception as exc:
                # Ensure consistent state on failure
                with self._state_lock:
                    self.playing = False
                    self.play_pending = False
                    self.current_track = None
                logger.error(f"Failed to stop: {exc}")
                raise

    def next_track(self):
        if self.device and self.device.is_connected:
            try:
                with self._state_lock:
                    self.play_pending = True
                self.device.next_track()
            except Exception as exc:
                with self._state_lock:
                    self.playing = False  # Ensure consistent state on failure
                    self.play_pending = False
                logger.error(f"Failed to skip to next track: {exc}")
                raise

    def prev_track(self):
        if self.device and self.device.is_connected:
            try:
                with self._state_lock:
                    self.play_pending = True
                self.device.prev_track()
            except Exception as exc:
                with self._state_lock:
                    self.playing = False  # Ensure consistent state on failure
                    self.play_pending = False
                logger.error(f"Failed to skip to previous track: {exc}")
                raise

    def play_track(self, track_id: Any):
        number = int(track_id)
        if self.device and self.device.is_connected:
            try:
                self.device.play_track(number)
                with self._state_lock:
                    self.play_pending = True  # Listener will set current_track and playing when 0x3E received
            except Exception as exc:
                # Reset state on failure
                with self._state_lock:
                    self.play_pending = False
                logger.error(f"Failed to play track {number}: {exc}")
                raise

    def set_volume(self, volume: int):
        volume = max(0, min(30, int(volume)))
        if self.device and self.device.is_connected:
            try:
                self.device.set_volume(volume)
                with self._state_lock:
                    self.volume_level = volume  # Update state only after successful hardware call
            except Exception as exc:
                logger.error(f"Failed to set volume: {exc}")
        else:
            # No device connected, just update cached value
            with self._state_lock:
                self.volume_level = volume

    # Status --------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        with self._dropped_events_lock:
            dropped_events = self._dropped_events

        with self._state_lock:
            playing = self.playing
            track_number = self.current_track
            volume = self.volume_level

        with self._device_lock:
            connected = self.device.is_connected if self.device else False
            has_device = self.device is not None

        status = {
            "playing": playing,
            "track_number": track_number,
            "volume": volume,
            "connected": connected,
            "error": None,
            "dropped_events": dropped_events,  # Include dropped event count for monitoring
        }
        if has_device and not connected:
            status["error"] = "DFPlayer not connected"
        return status

    def poll_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        try:
            return self._event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # Internal listener --------------------------------------------
    def _start_listener(self) -> None:
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._stop_event.clear()  # Clear stop signal
        self._listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self._listener_thread.start()

    def _stop_listener(self) -> None:
        self._stop_event.set()  # Signal thread to stop
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5.0)
            if self._listener_thread.is_alive():
                logger.warning("Listener thread did not terminate within 5.0s timeout")
        self._listener_thread = None

    def _listener_loop(self) -> None:
        logger.debug("DFPlayer backend listener started")
        while not self._stop_event.is_set():
            with self._device_lock:
                dev = self.device
            if not dev or not getattr(dev, "is_connected", False):
                break
            try:
                response = dev.read_response(timeout=0.1)
            except Exception as exc:
                logger.debug(f"DFPlayer read error: {exc}")
                continue

            if not response:
                continue

            cmd = response[3]
            try:
                if cmd == 0x3D:
                    self._event_queue.put({"type": "track_finished"}, block=False)
                    with self._state_lock:
                        self.playing = False
                        self.play_pending = False
                elif cmd == 0x3E:
                    track_num = (response[5] << 8) | response[6]
                    self._event_queue.put({"type": "track_started", "track": track_num}, block=False)
                    with self._state_lock:
                        self.current_track = track_num  # Set current_track based on hardware feedback
                        self.playing = True
                        self.play_pending = False
                elif cmd == 0x40:
                    self._event_queue.put({"type": "error", "code": response[6]}, block=False)
            except queue.Full:
                with self._dropped_events_lock:
                    self._dropped_events += 1
                    dropped_count = self._dropped_events
                logger.warning(f"Event queue full, dropping event (total dropped: {dropped_count})")

    @property
    def is_connected(self) -> bool:
        with self._device_lock:
            return self.device is not None and getattr(self.device, "is_connected", False)
