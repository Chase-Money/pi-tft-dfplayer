"""Main application class for the v2 UI framework."""
from __future__ import annotations

import atexit
import logging
import time
from typing import Dict, List, Optional, Tuple

from core.config import Config
from core.application_config import ApplicationConfig
from core.runtime_state import RuntimeState
from core.state import get_state
from utils.track_catalog import load_track_catalog
from utils.metadata import load_metadata
from hardware.framebuffer import Framebuffer
from hardware.touch_controller import TouchController
from backends.dfplayer import DFPlayerBackend
from ui.framework.manager import ScreenManagerV2
from ui.framework.events import UIEvent
from ui.renderer import FramebufferRendererV2
from ui.screens.home import HomeScreen
from ui.screens.track_browser import TrackBrowserScreen
from ui.screens.now_playing import NowPlayingScreen
from ui.screens.settings import SettingsScreen
from ui.screens.calibration import CalibrationScreen

logger = logging.getLogger(__name__)


class Application:
    """Unified touchscreen application built on the ScreenManagerV2 stack."""

    # Performance constants
    TARGET_FPS = 30  # Target frame rate for UI rendering
    MAX_EVENTS_PER_FRAME = 100  # Safety limit for backend event processing
    # Watchdog heartbeat logs at INFO level to detect freezes. Set to higher value
    # (e.g., 300.0 for 5min) for long-running devices to reduce log spam, or disable
    # entirely by setting to 0 (not recommended for production).
    WATCHDOG_INTERVAL = 300.0  # Watchdog heartbeat interval in seconds (5 minutes)

    def __init__(self, config=None) -> None:
        self.config: Config = config or Config()
        self.config.load()
        self.app_config = self.config.to_application_config()
        self.runtime_state = RuntimeState()
        self.runtime_state.hydrate_from_config(self.app_config)

        try:
            self.framebuffer = Framebuffer()
        except Exception as exc:
            logger.error("Failed to open framebuffer: %s", exc)
            raise

        try:
            self.touch_controller = TouchController(config=self.config)
            # Load and apply calibration and orientation from config
            if self.touch_controller:
                cal = self.app_config.touch.calibration
                self.touch_controller.set_calibration(
                    cal["min_x"], cal["max_x"], cal["min_y"], cal["max_y"]
                )
                orient = self.app_config.touch.orientation
                self.touch_controller.set_orientation(
                    swap_xy=orient["swap_xy"],
                    flip_x=orient["flip_x"],
                    flip_y=orient["flip_y"]
                )
                logger.info(f"Touch calibration applied: {cal}")
                logger.info(f"Touch orientation applied: {orient}")
        except Exception as exc:
            logger.error("Failed to initialize touch input: %s", exc)
            self.touch_controller = None

        self.state = get_state()
        self.backend = DFPlayerBackend()
        if not self.backend.initialize():
            logger.warning("DFPlayer backend failed to initialize; UI will run in demo mode")
            self.backend = None
        else:
            volume = self.app_config.audio.volume
            self.state.set_volume(volume)
            self.backend.set_volume(volume)

        self._load_tracks_and_metadata()

        services = {
            "state": self.state,
            "backend": self.backend,
            "config": self.config,
            "app_config": self.app_config,
            "runtime_state": self.runtime_state,
            "app": self,
            "renderer": None,
        }
        self.screen_manager = ScreenManagerV2(services)
        self.screen_manager.register("home", HomeScreen)
        self.screen_manager.register("track_browser", TrackBrowserScreen)
        self.screen_manager.register("now_playing", NowPlayingScreen)
        self.screen_manager.register("settings", SettingsScreen)
        self.screen_manager.register("calibration", CalibrationScreen)
        self.screen_manager.push("home")

        self.renderer = FramebufferRendererV2(self.framebuffer, self.screen_manager)
        self.screen_manager.services["renderer"] = self.renderer
        self.running = True

        # Track dropped events for UI warnings
        self._last_dropped_count = 0
        self._last_drop_warn_ts = 0.0

        # Watchdog for freeze detection
        self._last_watchdog_time = 0.0
        self._frame_count = 0

        # Status message display
        self._status_message: Optional[str] = None
        self._status_level: str = "info"
        self._status_expires_at: float = 0.0
        self._status_changed: bool = False
        self._status_was_visible: bool = False  # Track if status was visible last frame

        atexit.register(self.cleanup)

    def _load_tracks_and_metadata(self) -> None:
        catalog_path = self.app_config.paths.track_catalog or self.config.get_track_catalog_path()
        catalog = load_track_catalog(catalog_path)
        track_dicts = self._tracks_to_dicts(catalog)
        self.state.set_tracks(track_dicts)

        metadata = load_metadata(
            self.app_config.paths.metadata or self.config.get_metadata_path(),
            self.app_config.paths.artwork_root or self.config.get_artwork_root(),
        )
        self.state.set_metadata(metadata)

        if self.state.tracks:
            self.state.select_track_index(0)

    @staticmethod
    def _tracks_to_dicts(tracks: List[object]) -> List[Dict[str, object]]:
        result: List[Dict[str, object]] = []
        for track in tracks:
            if hasattr(track, "number"):
                result.append(
                    {
                        "number": getattr(track, "number"),
                        "title": getattr(track, "title", "Unknown"),
                        "artist": getattr(track, "artist", None),
                        "artwork": getattr(track, "artwork_path", None),
                    }
                )
            elif isinstance(track, dict):
                result.append(track)
        return result

    # ------------------------------------------------------------------
    # Main loop
    def run(self) -> None:
        logger.info("Starting v2 Application loop")
        self.renderer.render(); self.renderer.present()

        if not self.touch_controller or not getattr(self.touch_controller, "available", False):
            logger.warning("Touch input unavailable; rendered one frame")
            return

        # Frame rate limiting: target frames per second (33.3ms per frame at 30fps)
        frame_time = 1.0 / self.TARGET_FPS
        next_frame_time = time.monotonic()

        while self.running:
            frame_start = time.monotonic()

            refreshed = self._drain_backend_events()

            # Check for dropped events and warn user
            if self.backend and hasattr(self.backend, 'get_status'):
                status = self.backend.get_status()
                dropped = status.get('dropped_events', 0)
                now = time.monotonic()
                if dropped > self._last_dropped_count and (dropped - self._last_dropped_count >= 5 or now - self._last_drop_warn_ts >= 5.0):
                    count = dropped - self._last_dropped_count
                    self.set_status(f"⚠ {count} playback events dropped", "warning", 5)
                    self._last_dropped_count = dropped
                    self._last_drop_warn_ts = now

            events = self.touch_controller.get_events(timeout=0)
            for evt in events:
                ui_evt = self._touch_to_ui_event(evt)
                if ui_evt:
                    self.screen_manager.handle_event(ui_evt)
                    refreshed = True

            # Check if status message visibility changed (new message or expiration)
            status_visible = self.get_status() is not None
            if self._status_changed or (status_visible != self._status_was_visible):
                refreshed = True
                self._status_changed = False
                self._status_was_visible = status_visible

            if refreshed:
                # Force full screen refresh after screen navigation to prevent artifacts
                if self.screen_manager.needs_full_refresh():
                    logger.info("[APP] Full screen refresh after navigation")
                    dirty = None
                    self.screen_manager.clear_refresh_flag()
                else:
                    # Get dirty rect hints from screen if available (for partial updates)
                    # Defaults to None for full screen update if screen doesn't provide hints
                    dirty = getattr(self.screen_manager.current, "last_dirty", None)
                self.renderer.render()
                self.renderer.present(dirty_rects=dirty)

            # Frame rate limiting: sleep to maintain 30fps
            now = time.monotonic()
            sleep_for = next_frame_time - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                next_frame_time += frame_time
            else:
                # We're behind; catch up without drifting
                next_frame_time = now + frame_time

            # Watchdog heartbeat: log periodic status to detect freezes
            self._frame_count += 1
            if now - self._last_watchdog_time >= self.WATCHDOG_INTERVAL:
                fps = self._frame_count / (now - self._last_watchdog_time) if self._last_watchdog_time > 0 else 0
                logger.info(f"[WATCHDOG] Heartbeat: {self._frame_count} frames in {now - self._last_watchdog_time:.1f}s (avg {fps:.1f} fps)")
                self._frame_count = 0
                self._last_watchdog_time = now

    def _touch_to_ui_event(self, touch_event) -> Optional[UIEvent]:
        event_type = getattr(touch_event, "type", None)
        x = getattr(touch_event, "x", None)
        y = getattr(touch_event, "y", None)
        dx = getattr(touch_event, "dx", 0)
        dy = getattr(touch_event, "dy", 0)
        direction = getattr(touch_event, "direction", None)
        raw_x = getattr(touch_event, "raw_x", None)
        raw_y = getattr(touch_event, "raw_y", None)

        # Record touch for debug visualization
        if x is not None and y is not None and self.renderer:
            self.renderer.touch_debug.record_touch(x, y)

        # Include raw coordinates for calibration screen
        raw = (raw_x, raw_y) if raw_x is not None and raw_y is not None else None

        if event_type == "tap":
            logger.info(f"[TOUCH] TAP at ({x}, {y})")
            return UIEvent("tap", {"pos": (x, y), "raw": raw})
        if event_type == "drag":
            return UIEvent("drag", {"pos": (x, y), "dx": dx, "dy": dy, "raw": raw})
        if event_type == "swipe":
            return UIEvent("swipe", {"direction": direction, "delta": max(abs(dx), abs(dy)), "raw": raw})
        if event_type == "press":
            logger.info(f"[TOUCH] PRESS at ({x}, {y})")
            return UIEvent("press", {"pos": (x, y), "raw": raw})
        if event_type == "release":
            logger.info(f"[TOUCH] RELEASE at ({x}, {y})")
            return UIEvent("release", {"pos": (x, y), "raw": raw})
        return None

    def _drain_backend_events(self) -> bool:
        """
        Drain pending backend events with safety limit.

        Returns:
            bool: True if any event triggered a UI refresh
        """
        if not self.backend:
            return False

        # Check if backend supports event polling (not all backends do)
        if not hasattr(self.backend, 'poll_event'):
            return False

        refreshed = False
        # Event drain loop performance: processes up to MAX_EVENTS_PER_FRAME events per frame
        # At 30fps (33ms/frame), this gives ~330µs per event budget
        # Sufficient for Pi Zero 2 W @ 1GHz - events rarely stack beyond 5-10 in practice
        event_count = 0

        while event_count < self.MAX_EVENTS_PER_FRAME:
            event = self.backend.poll_event(timeout=0)
            if not event:
                break
            event_count += 1

            etype = event.get("type")
            if etype == "track_finished":
                track = self.state.advance_track(1)
                if track:
                    try:
                        self.backend.play_track(track.number)
                        self.state.start_playback(self.state.playback.selected_track_index)
                        refreshed = True
                    except Exception as exc:
                        logger.error(f"Failed to play next track {track.number}: {exc}")
                        self.set_status(f"Playback error: {exc}", "error", 5)
            elif etype == "track_started":
                number = event.get("track")
                idx = self.state.get_index_by_number(number) if number is not None else None
                if idx is not None:
                    self.state.start_playback(idx)
                    refreshed = True
            elif etype == "error":
                code = event.get("code")
                logger.error("DFPlayer error 0x%02x", code if isinstance(code, int) else 0)

        if event_count >= self.MAX_EVENTS_PER_FRAME:
            logger.warning(f"Event drain limit reached ({self.MAX_EVENTS_PER_FRAME} events), some events may be pending")

        return refreshed

    def get_status(self) -> Optional[Tuple[str, str]]:
        """Return optional status banner (message, level) for UI display."""
        if self._status_message and time.monotonic() < self._status_expires_at:
            return (self._status_message, self._status_level)
        return None

    def set_status(self, message: str, level: str = "info", timeout: int = 3) -> None:
        """
        Set temporary status message for UI display.

        Args:
            message: The status message to display
            level: Message level (info, warning, error)
            timeout: How many seconds to display the message
        """
        logger.info(f"Status [{level}]: {message}")
        self._status_message = message
        self._status_level = level
        self._status_expires_at = time.monotonic() + timeout
        self._status_changed = True

    def get_touch_driver_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get raw touch driver bounds (min_x, max_x, min_y, max_y)."""
        if not self.touch_controller or not self.touch_controller.touch:
            return None
        return (
            self.touch_controller.touch.min_x,
            self.touch_controller.touch.max_x,
            self.touch_controller.touch.min_y,
            self.touch_controller.touch.max_y,
        )

    def get_touch_orientation(self) -> dict:
        """Get current touch orientation settings."""
        if not self.touch_controller or not self.touch_controller.touch:
            return {"swap_xy": False, "flip_x": False, "flip_y": False}
        return self.touch_controller.touch.orientation

    def set_touch_calibration(self, bounds: Tuple[int, int, int, int]) -> None:
        """Set and save touch calibration bounds."""
        min_x, max_x, min_y, max_y = bounds
        logger.info(f"Setting touch calibration: ({min_x}, {max_x}, {min_y}, {max_y})")

        try:
            # Apply to touch controller
            if self.touch_controller:
                self.touch_controller.set_calibration(min_x, max_x, min_y, max_y)

            # Save to config (validates bounds)
            self.config.set_touch_calibration(min_x, max_x, min_y, max_y)
            self.config.save()
        except ValueError as e:
            logger.error(f"Invalid calibration bounds: {e}")
            self.set_status(f"Calibration error: {e}", "error", 5)
            raise

    def cleanup(self) -> None:
        self.running = False
        if self.backend:
            try:
                self.backend.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down backend: {e}")
        if hasattr(self.framebuffer, "close"):
            try:
                self.framebuffer.close()
            except Exception as e:
                logger.error(f"Error closing framebuffer: {e}")
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        Application().run()
    except KeyboardInterrupt:
        logger.info("Exiting v2 application")
