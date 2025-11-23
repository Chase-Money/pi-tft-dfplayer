"""Main application class for the v2 UI framework."""
from __future__ import annotations

import atexit
import logging
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from core.config_v2 import Config as ConfigV2
from core.state import ApplicationState, get_state
from utils.track_catalog import load_track_catalog
from utils.metadata import load_metadata
from hardware.framebuffer import Framebuffer
from hardware.touch_controller import TouchController
from backends.dfplayer_v2 import DFPlayerBackend
from ui.framework.manager import ScreenManagerV2
from ui.framework.events import UIEvent
from ui.screens.home import HomeScreen
from ui.screens.track_browser import TrackBrowserScreen
from ui.screens.now_playing import NowPlayingScreen

logger = logging.getLogger(__name__)


class Application:
    """Unified touchscreen application built on the ScreenManagerV2 stack."""

    def __init__(self, config=None) -> None:
        self.config: ConfigV2 = config or ConfigV2()
        self.config.load()

        try:
            self.framebuffer = Framebuffer()
        except Exception as exc:
            logger.error("Failed to open framebuffer: %s", exc)
            raise

        try:
            self.touch_controller = TouchController(config=self.config)
        except Exception as exc:
            logger.error("Failed to initialize touch input: %s", exc)
            self.touch_controller = None
        self.fonts = self._load_fonts()

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
        }
        self.screen_manager = ScreenManagerV2(services)
        self.screen_manager.register("home", HomeScreen)
        self.screen_manager.register("track_browser", TrackBrowserScreen)
        self.screen_manager.register("now_playing", NowPlayingScreen)
        self.screen_manager.push("home")

        self.image = Image.new("RGB", (self.framebuffer.width, self.framebuffer.height), (12, 16, 24))
        self.draw = ImageDraw.Draw(self.image)
        self.running = True

        atexit.register(self.cleanup)

    # ------------------------------------------------------------------
    # Initialization helpers
    def _configure_touch(self) -> None:
        """Apply orientation/calibration settings for compatibility (legacy path)."""
        # TouchController handles orientation/calibration internally via config; no-op retained for compatibility.
        return

    def _load_fonts(self) -> Dict[str, ImageFont.ImageFont]:
        fonts = {
            "large": ImageFont.load_default(),
            "medium": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }
        try:
            fonts["large"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            fonts["medium"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            fonts["small"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except Exception as exc:
            logger.warning("Falling back to default fonts: %s", exc)
        return fonts

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
        self.render()
        self.framebuffer.push(self.image)

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
                self.render()
                self.framebuffer.push(self.image)

    def _touch_to_ui_event(self, touch_event) -> Optional[UIEvent]:
        event_type = getattr(touch_event, "type", None)
        x = getattr(touch_event, "x", None)
        y = getattr(touch_event, "y", None)
        dx = getattr(touch_event, "dx", 0)
        dy = getattr(touch_event, "dy", 0)
        direction = getattr(touch_event, "direction", None)

        if event_type == "tap":
            return UIEvent("tap", {"pos": (x, y)})
        if event_type == "drag":
            return UIEvent("drag", {"pos": (x, y), "dx": dx, "dy": dy})
        if event_type == "swipe":
            return UIEvent("swipe", {"direction": direction, "delta": max(abs(dx), abs(dy))})
        if event_type == "press":
            return UIEvent("press", {"pos": (x, y)})
        if event_type == "release":
            return UIEvent("release", {"pos": (x, y)})
        return None

    def _drain_backend_events(self) -> bool:
        """
        Drain pending backend events with safety limit.

        Returns:
            bool: True if any event triggered a UI refresh
        """
        if not self.backend:
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

    # ------------------------------------------------------------------
    def render(self) -> None:
        # Calculate scale factor based on screen dimensions (reference: 480x320)
        scale = min(self.framebuffer.width / 480, self.framebuffer.height / 320)

        context = {
            "image": self.image,
            "draw": self.draw,
            "fonts": self.fonts,
            "state": self.state,
            "scale": scale,
        }
        self.screen_manager.render(context)

    def get_status(self) -> Optional[Tuple[str, str]]:
        """Return optional status banner (message, level) for UI display."""
        # Future: Return status messages for system events
        # e.g., ("Low battery", "warning") or ("Track loaded", "info")
        return None

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
