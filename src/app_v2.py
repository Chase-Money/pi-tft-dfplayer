"""Main application class for the v2 UI framework."""
from __future__ import annotations

import atexit
import logging
import select
import statistics
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from core.config import ORIENTS, get_config
from core.state_v2 import AppState
from utils.track_catalog import load_track_catalog
from utils.metadata import load_metadata
from hardware.framebuffer import Framebuffer
from hardware.touch import TouchInput, EVDEV_AVAILABLE
from backends.dfplayer_backend import DFPlayerBackend
from ui.framework_v2.manager import ScreenManagerV2
from ui.framework_v2.events import UIEvent
from ui.screens_v2.home import HomeScreen
from ui.screens_v2.track_browser import TrackBrowserScreen
from ui.screens_v2.now_playing import NowPlayingScreen

logger = logging.getLogger(__name__)


class Application:
    """Unified touchscreen application built on the ScreenManagerV2 stack."""

    def __init__(self, config=None) -> None:
        self.config = config or get_config()
        try:
            self.framebuffer = Framebuffer()
        except Exception as exc:
            logger.error("Failed to open framebuffer: %s", exc)
            raise

        try:
            self.touch = TouchInput()
        except Exception as exc:
            logger.error("Failed to initialize touch input: %s", exc)
            self.touch = None
        self._configure_touch()
        self.fonts = self._load_fonts()

        self.state = AppState()
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
        self._touching = False
        self._drag_start: Optional[Tuple[int, int]] = None
        self._last_touch: Optional[Tuple[int, int]] = None
        self._dragged = False

        atexit.register(self.cleanup)

    # ------------------------------------------------------------------
    # Initialization helpers
    def _configure_touch(self) -> None:
        """Apply orientation/calibration settings and non-blocking mode."""
        if not EVDEV_AVAILABLE or not self.touch or not getattr(self.touch, "device", None):
            logger.warning("Touch device not available; application will render one frame")
            return

        self.touch.screen_width = self.framebuffer.width
        self.touch.screen_height = self.framebuffer.height

        orientation_index = self.config.get_touch_orientation()
        orient = ORIENTS[orientation_index % len(ORIENTS)]
        self.touch.orientation = orient.copy()

        calibration = self.config.get_touch_calibration()
        if calibration:
            self.touch.calibration = calibration

        try:
            self.touch.device.set_blocking(False)
        except Exception:
            pass

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

        if not EVDEV_AVAILABLE or not self.touch or self.touch.fileno() < 0:
            logger.warning("Touch input unavailable; rendered one frame")
            return

        fd = self.touch.fileno()
        raw_x: List[int] = []
        raw_y: List[int] = []

        while self.running:
            refreshed = self._drain_backend_events()
            try:
                rlist, _, _ = select.select([fd], [], [], 0.05)
            except (OSError, ValueError):
                continue

            if rlist:
                refreshed = self._process_touch_events(raw_x, raw_y) or refreshed

            if refreshed:
                self.render()
                self.framebuffer.push(self.image)

    def _process_touch_events(self, raw_x: List[int], raw_y: List[int]) -> bool:
        from evdev import ecodes

        updated = False
        while True:
            event = self.touch.read_event()
            if event is None:
                break

            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                self._touching = event.value == 1
                if self._touching:
                    raw_x.clear()
                    raw_y.clear()
                    self._drag_start = None
                    self._last_touch = None
                    self._dragged = False
                else:
                    if self._last_touch:
                        if self._dragged:
                            self._dispatch_drag_end(self._last_touch)
                        else:
                            self._dispatch_tap(self._last_touch)
                            updated = True
                    self._drag_start = None
                    self._last_touch = None
                    self._dragged = False
            elif event.type == ecodes.EV_ABS and self._touching:
                if event.code == ecodes.ABS_X:
                    raw_x.append(event.value)
                elif event.code == ecodes.ABS_Y:
                    raw_y.append(event.value)

                if len(raw_x) >= 4 and len(raw_y) >= 4:
                    px, py = self._scale_touch(raw_x, raw_y)
                    if self._drag_start is None:
                        self._drag_start = (px, py)
                    prev = self._last_touch
                    self._last_touch = (px, py)
                    if not self._dragged and self._drag_start:
                        dx = abs(px - self._drag_start[0])
                        dy = abs(py - self._drag_start[1])
                        if max(dx, dy) > 6:
                            self._dragged = True
                    payload = {"pos": (px, py), "start": self._drag_start}
                    if prev:
                        payload["prev"] = prev
                    self.screen_manager.handle_event(UIEvent("drag", payload))
                    updated = True
        return updated

    def _scale_touch(self, raw_x: List[int], raw_y: List[int]) -> Tuple[int, int]:
        med_rx = int(statistics.median(raw_x[-6:]))
        med_ry = int(statistics.median(raw_y[-6:]))
        return self.touch.scale_xy(med_rx, med_ry)

    def _dispatch_tap(self, pos: Tuple[int, int]) -> None:
        self.screen_manager.handle_event(UIEvent("tap", {"pos": pos}))

    def _dispatch_drag_end(self, pos: Tuple[int, int]) -> None:
        payload = {"pos": pos}
        if self._drag_start:
            payload["start"] = self._drag_start
        self.screen_manager.handle_event(UIEvent("drag_end", payload))

    def _drain_backend_events(self) -> bool:
        if not self.backend:
            return False
        refreshed = False
        while True:
            event = self.backend.poll_event(timeout=0)
            if not event:
                break
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
        return refreshed

    # ------------------------------------------------------------------
    def render(self) -> None:
        context = {
            "image": self.image,
            "draw": self.draw,
            "fonts": self.fonts,
            "state": self.state,
        }
        self.screen_manager.render(context)

    def cleanup(self) -> None:
        self.running = False
        if self.backend:
            try:
                self.backend.shutdown()
            except Exception:
                pass
        if hasattr(self.framebuffer, "close"):
            try:
                self.framebuffer.close()
            except Exception:
                pass
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        Application().run()
    except KeyboardInterrupt:
        logger.info("Exiting v2 application")
