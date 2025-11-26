"""Main application class for the v2 UI framework."""
from __future__ import annotations

import atexit
import logging
from typing import Dict, List, Optional, Tuple

from core.config import Config
from core.state import get_state
from utils.track_catalog import load_track_catalog
from utils.metadata import load_metadata
from hardware.framebuffer import Framebuffer
from hardware.touch_controller import TouchController
from backends.dfplayer_v2 import DFPlayerBackend
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

    def __init__(self, config=None) -> None:
        self.config: Config = config or Config()
        self.config.load()

        try:
            self.framebuffer = Framebuffer()
        except Exception as exc:
            logger.error("Failed to open framebuffer: %s", exc)
            raise

        try:
            self.touch_controller = TouchController(config=self.config)
            # Load and apply calibration and orientation from config
            if self.touch_controller:
                cal = self.config.get_touch_calibration()
                self.touch_controller.set_calibration(
                    cal["min_x"], cal["max_x"], cal["min_y"], cal["max_y"]
                )
                orient = self.config.get_touch_orientation()
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
            volume = self.config.get_volume()
            self.state.set_volume(volume)
            self.backend.set_volume(volume)

        self._load_tracks_and_metadata()

        services = {
            "state": self.state,
            "backend": self.backend,
            "config": self.config,
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

        atexit.register(self.cleanup)

    def _load_tracks_and_metadata(self) -> None:
        catalog = load_track_catalog(self.config.get_track_catalog_path())
        track_dicts = self._tracks_to_dicts(catalog)
        self.state.set_tracks(track_dicts)

        metadata = load_metadata(
            self.config.get_metadata_path(),
            self.config.get_artwork_root(),
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

        while self.running:
            refreshed = self._drain_backend_events()
            events = self.touch_controller.get_events(timeout=0)
            for evt in events:
                ui_evt = self._touch_to_ui_event(evt)
                if ui_evt:
                    self.screen_manager.handle_event(ui_evt)
                    refreshed = True

            if refreshed:
                dirty = getattr(self.screen_manager.current, "last_dirty", None)
                self.renderer.render(); self.renderer.present(dirty_rects=dirty)

    def _touch_to_ui_event(self, touch_event) -> Optional[UIEvent]:
        event_type = getattr(touch_event, "type", None)
        x = getattr(touch_event, "x", None)
        y = getattr(touch_event, "y", None)
        dx = getattr(touch_event, "dx", 0)
        dy = getattr(touch_event, "dy", 0)
        direction = getattr(touch_event, "direction", None)
        raw_x = getattr(touch_event, "raw_x", None)
        raw_y = getattr(touch_event, "raw_y", None)

        # Include raw coordinates for calibration screen
        raw = (raw_x, raw_y) if raw_x is not None and raw_y is not None else None

        if event_type == "tap":
            return UIEvent("tap", {"pos": (x, y), "raw": raw})
        if event_type == "drag":
            return UIEvent("drag", {"pos": (x, y), "dx": dx, "dy": dy, "raw": raw})
        if event_type == "swipe":
            return UIEvent("swipe", {"direction": direction, "delta": max(abs(dx), abs(dy)), "raw": raw})
        if event_type == "press":
            return UIEvent("press", {"pos": (x, y), "raw": raw})
        if event_type == "release":
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
        max_events = 100  # Safety limit to prevent infinite loop if events flood
        event_count = 0

        while event_count < max_events:
            event = self.backend.poll_event(timeout=0)
            if not event:
                break
            event_count += 1

            etype = event.get("type")
            if etype == "track_finished":
                track = self.state.advance_track(1)
                if track:
                    self.backend.play_track(track.number)
                    self.state.start_playback(self.state.playback.selected_track_index)
                    refreshed = True
            elif etype == "track_started":
                number = event.get("track")
                idx = self.state.get_index_by_number(number) if number is not None else None
                if idx is not None:
                    self.state.start_playback(idx)
                    refreshed = True
            elif etype == "error":
                code = event.get("code")
                logger.error("DFPlayer error 0x%02x", code if isinstance(code, int) else 0)

        if event_count >= max_events:
            logger.warning(f"Event drain limit reached ({max_events} events), some events may be pending")

        return refreshed

    def get_status(self) -> Optional[Tuple[str, str]]:
        """Return optional status banner (message, level) for UI display."""
        return None

    def set_status(self, message: str, level: str = "info", timeout: int = 3) -> None:
        """
        Set temporary status message for UI display.

        Currently logs the status message. Future enhancement: implement
        a status message queue with timeout for on-screen notifications.
        """
        logger.info(f"Status [{level}]: {message}")

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
