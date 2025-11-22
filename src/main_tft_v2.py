#!/usr/bin/env python3
"""
Main entry point for TFT touch screen variant using V2 framework.

This application integrates:
- ILI9486 framebuffer (/dev/fb0 or /dev/fb1)
- XPT2046/ADS7846 touch controller
- DFPlayer Mini backend
- V2 UI framework with screen manager
- FramebufferRendererV2
"""

import logging
import os
import sys
import time
import atexit
from typing import Optional, Tuple

from core.state import get_state, ApplicationState
from core.config import get_config, ORIENTS
from backends.dfplayer_v2 import DFPlayerBackend
from hardware.framebuffer import Framebuffer
from hardware.touch_controller import TouchController
from ui.framework_v2.manager import ScreenManagerV2
from ui.framework_v2.events import UIEvent
from ui.renderer_v2 import FramebufferRendererV2

# Import V2 screens
from ui.screens_v2.home import HomeScreen
from ui.screens_v2.track_browser import TrackBrowserScreen
from ui.screens_v2.now_playing import NowPlayingScreen
from utils.track_catalog import load_track_catalog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DFPlayerTFTApp:
    """
    Main application class for TFT touch screen variant.

    Coordinates all subsystems:
    - Framebuffer rendering
    - Touch input processing
    - Screen navigation
    - DFPlayer playback backend
    - Application state
    """

    def __init__(
        self,
        fb_device: str = "/dev/fb1",
        touch_device: Optional[str] = None
    ):
        """
        Initialize the application.

        Args:
            fb_device: Framebuffer device path (default: /dev/fb0)
            touch_device: Touch device path (default: auto-detect)
        """
        self.fb_device = fb_device
        self.touch_device = touch_device

        self.config = get_config()

        # Core components (initialized in _init_*)
        self.framebuffer: Optional[Framebuffer] = None
        self.touch: Optional[TouchController] = None
        self.backend: Optional[DFPlayerBackend] = None
        self.state: Optional[AppState] = None
        self.screen_manager: Optional[ScreenManagerV2] = None
        self.renderer: Optional[FramebufferRendererV2] = None

        # Runtime state
        self.running = False
        self.orientation_index = self.config.get_touch_orientation()
        self._status_message: Optional[str] = None
        self._status_level: str = "info"
        self._status_expiry: float = 0.0

        # Register cleanup handler
        atexit.register(self.cleanup)

    def initialize(self) -> bool:
        """
        Initialize all subsystems.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            logger.info("Initializing DFPlayer TFT Application")

            # Initialize hardware (framebuffer is required, touch is optional)
            if not self._init_framebuffer():
                logger.error("Framebuffer initialization failed - cannot continue")
                return False

            if not self._init_touch():
                logger.warning("Touch controller initialization failed - continuing without touch input")
                self.set_status("Touch controller unavailable", level="warning", duration=6)
            # Continue anyway - app can still run without touch for testing

            # Initialize backend (optional - app can run without DFPlayer)
            if not self._init_backend():
                logger.warning("DFPlayer backend initialization failed - continuing anyway")
                self.set_status("DFPlayer backend unavailable", level="warning", duration=6)

            # Initialize state (always succeeds with fallback tracks)
            try:
                self._init_state()
            except Exception as e:
                logger.error(f"State initialization failed: {e}", exc_info=True)
                self.set_status("Unable to initialize track catalog", level="error", duration=6)
                return False

            # Initialize UI framework (critical)
            try:
                self._init_screen_manager()
                self._init_renderer()
            except Exception as e:
                logger.error(f"UI framework initialization failed: {e}", exc_info=True)
                return False

            # Register screens (critical)
            try:
                self._register_screens()
            except Exception as e:
                logger.error(f"Screen registration failed: {e}", exc_info=True)
                return False

            logger.info("Application initialization complete")
            if not self.touch:
                self.set_status("Touch disabled: check wiring", level="warning", duration=8)
            if self.state and not self.state.tracks:
                self.set_status("No tracks found", level="warning", duration=6)
            logger.info(f"  Framebuffer: {'OK' if self.framebuffer else 'FAILED'}")
            logger.info(f"  Touch: {'OK' if self.touch else 'NOT AVAILABLE'}")
            logger.info(f"  Backend: {'OK' if self.backend else 'NOT AVAILABLE'}")
            logger.info(f"  Tracks: {len(self.state.tracks) if self.state else 0}")
            return True

        except Exception as e:
            logger.error(f"Initialization failed with unexpected error: {e}", exc_info=True)
            return False

    def _init_framebuffer(self) -> bool:
        """Initialize the framebuffer."""
        try:
            self.framebuffer = Framebuffer(device=self.fb_device)
            logger.info(f"Framebuffer initialized: {self.framebuffer.width}x{self.framebuffer.height}")
            logger.info(f"Framebuffer device: {self.framebuffer.device}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize framebuffer: {e}")
            return False

    def _init_touch(self) -> bool:
        """Initialize the touch controller."""
        try:
            self.touch = TouchController(device=self.touch_device, config=self.config)
            logger.info("Touch controller initialized")
            self._apply_touch_settings()
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize touch controller: {e}")
            self.touch = None
            return False

    def _init_backend(self) -> bool:
        """Initialize the DFPlayer backend."""
        try:
            self.backend = DFPlayerBackend()
            if self.backend.initialize():
                logger.info("DFPlayer backend initialized")
                return True
            else:
                logger.warning("DFPlayer backend initialization returned False")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize DFPlayer backend: {e}")
            return False

    def _load_tracks(self) -> list:
        """
        Load track catalog from file or DFPlayer query.

        Searches for catalog file in multiple locations:
        1. DFPLAYER_TRACK_CATALOG environment variable
        2. config/track_catalog.txt (relative to project root)
        3. /boot/dfplayer_tracks.txt
        4. Query DFPlayer for file count (fallback)

        File format (one track per line):
        - "number|title" format (pipe-separated)
        - "number title" format (space-separated)
        - Lines starting with # are comments

        Returns:
            list: List of track dictionaries
        """
        # Build search paths
        search_paths = []

        # Environment variable
        env_path = os.environ.get("DFPLAYER_TRACK_CATALOG")
        if env_path:
            search_paths.append(env_path)

        # Default locations
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        search_paths.extend([
            os.path.join(base_dir, "config", "track_catalog.txt"),
            "/boot/dfplayer_tracks.txt",
        ])

        # Try to load from each path
        for path in search_paths:
            if os.path.exists(path):
                tracks = self._parse_catalog_file(path)
                if tracks:
                    self.set_status(f"Loaded {len(tracks)} tracks", level="info", duration=4)
                    logger.info(f"Loaded {len(tracks)} tracks from {path}")
                    return tracks

        # Fallback: Query DFPlayer for file count
        if self.backend:
            try:
                file_count = self.backend.query_file_count()
                if file_count and file_count > 0:
                    logger.info(f"DFPlayer reported {file_count} files, generating placeholder tracks")
                    return [
                        {"number": i + 1, "title": f"Track {i + 1:03d}"}
                        for i in range(file_count)
                    ]
            except Exception as e:
                logger.warning(f"Failed to query DFPlayer file count: {e}")

        # Final fallback: Generate 30 placeholder tracks
        logger.warning("No track catalog found, generating 30 placeholder tracks")
        self.set_status("No track catalog found - using placeholders", level="warning", duration=6)
        return [
            {"number": i + 1, "title": f"Track {i + 1:03d}"}
            for i in range(30)
        ]

    def _parse_catalog_file(self, path: str) -> list:
        """
        Parse track catalog file.

        Args:
            path: Path to catalog file

        Returns:
            list: List of track dictionaries or empty list if parsing fails
        """
        tracks = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse line
                    try:
                        track = self._parse_catalog_line(line)
                        if track:
                            tracks.append(track)
                    except Exception as e:
                        logger.warning(f"Error parsing line {line_num} in {path}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to read catalog file {path}: {e}")
            return []

        if tracks:
            # Sort by track number
            tracks.sort(key=lambda t: t["number"])

        return tracks

    def _parse_catalog_line(self, line: str) -> Optional[dict]:
        """
        Parse single catalog line.

        Args:
            line: Catalog line

        Returns:
            dict: Track dictionary or None if invalid
        """
        # Try pipe-separated format first
        if "|" in line:
            num_str, title = line.split("|", 1)
            num_str = num_str.strip()
            title = title.strip()
        else:
            # Try space-separated format
            parts = line.split(None, 1)
            if not parts:
                return None

            num_str = parts[0]
            title = parts[1].strip() if len(parts) > 1 else ""

        # Parse track number
        try:
            track_no = int(num_str, 10)
        except ValueError:
            logger.warning(f"Invalid track number: {num_str}")
            return None

        # Default title if empty
        if not title:
            title = f"Track {track_no:03d}"

        return {"number": track_no, "title": title}

    def _init_state(self) -> None:
        """Initialize application state."""
        # Load tracks from catalog file
        tracks = load_track_catalog()

        self.state = get_state()
        self.state.set_tracks(tracks)
        logger.info(f"State initialized with {len(tracks)} tracks")

    def _init_screen_manager(self) -> None:
        """Initialize the screen manager with services."""
        services = {
            "state": self.state,
            "backend": self.backend,
            "app": self,
            "config": self.config,
        }

        self.screen_manager = ScreenManagerV2(services=services)
        logger.info("Screen manager initialized")

    def _init_renderer(self) -> None:
        """Initialize the renderer."""
        self.renderer = FramebufferRendererV2(
            framebuffer=self.framebuffer,
            screen_manager=self.screen_manager
        )
        logger.info("Renderer initialized")

    def _register_screens(self) -> None:
        """Register all available screens."""
        self.screen_manager.register("home", HomeScreen)
        self.screen_manager.register("track_browser", TrackBrowserScreen)
        self.screen_manager.register("now_playing", NowPlayingScreen)
        from ui.screens_v2.settings import SettingsScreen
        from ui.screens_v2.calibration import CalibrationScreen

        self.screen_manager.register("settings", SettingsScreen)
        self.screen_manager.register("calibration", CalibrationScreen)
        logger.info("Screens registered: home, track_browser, now_playing, settings, calibration")

    def run(self) -> None:
        """
        Main application loop.

        Processes touch events, renders UI, and presents to framebuffer.
        """
        if not all([self.framebuffer, self.screen_manager, self.renderer]):
            logger.error("Cannot run: initialization incomplete")
            return

        # Push initial screen
        self.screen_manager.push("home")

        # Initial render
        self.renderer.render_and_present()

        self.running = True
        logger.info("Entering main loop")

        frame_count = 0
        diag_count = 0
        last_fps_time = time.time()

        try:
            while self.running:
                # Periodic diagnostic logging (every 25 frames ~5 seconds at 5 FPS)
                if diag_count % 25 == 0:
                    current_screen = self.screen_manager.current.name if self.screen_manager.current else "None"
                    logger.info(f"[DIAG] Current screen: {current_screen}")
                    logger.info(f"[DIAG] Screen stack: {self.screen_manager.stack()}")
                    logger.info(f"[DIAG] Touch available: {self.touch is not None and getattr(self.touch, 'available', False)}")

                diag_count += 1

                # Process touch events
                if self.touch:
                    self._process_touch_events()

                # Render current screen
                self.renderer.render_and_present()

                # FPS tracking
                frame_count += 1
                now = time.time()
                if now - last_fps_time >= 5.0:
                    fps = frame_count / (now - last_fps_time)
                    logger.info(f"FPS: {fps:.1f}")
                    frame_count = 0
                    last_fps_time = now

                # Target ~30 FPS
                time.sleep(0.033)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.running = False

    def _process_touch_events(self) -> None:
        """
        Process touch events and route to screen manager.

        Converts touch controller events to UIEvent objects.
        """
        if not self.touch:
            return

        try:
            events = self.touch.get_events(timeout=0)  # Non-blocking

            for i, event in enumerate(events):
                logger.debug(f"[TOUCH] Processing event {i}: type={getattr(event, 'type', 'UNKNOWN')}, "
                             f"x={getattr(event, 'x', '?')}, y={getattr(event, 'y', '?')}")

                # Convert touch event to UIEvent
                ui_event = self._touch_to_ui_event(event)
                if ui_event:
                    logger.debug(f"[TOUCH] Created UIEvent: {ui_event.type}, routing to screen manager")
                    self.screen_manager.handle_event(ui_event)
                else:
                    logger.debug(f"[TOUCH] Failed to convert touch event to UIEvent")

        except Exception as e:
            logger.error(f"Error processing touch events: {e}")

    def _touch_to_ui_event(self, touch_event) -> Optional[UIEvent]:
        """
        Convert a touch controller event to a UIEvent.

        Args:
            touch_event: Event from touch controller

        Returns:
            UIEvent or None
        """
        # Map touch event types to UI events
        event_type = getattr(touch_event, 'type', None)
        x = getattr(touch_event, 'x', None)
        y = getattr(touch_event, 'y', None)
        raw_x = getattr(touch_event, 'raw_x', None)
        raw_y = getattr(touch_event, 'raw_y', None)

        logger.debug(f"[CONVERT] Touch event type={event_type}, coords=({x}, {y}), raw=({raw_x}, {raw_y})")

        raw_payload = {"raw": (raw_x, raw_y)} if raw_x is not None else {}

        if event_type == 'tap':
            logger.info(f"[CONVERT] Creating UIEvent TAP at ({x}, {y})")
            return UIEvent(
                "tap",
                payload={
                    "pos": (x, y),
                    **raw_payload
                }
            )
        elif event_type == 'drag':
            dx = getattr(touch_event, 'dx', 0)
            dy = getattr(touch_event, 'dy', 0)
            logger.info(f"[CONVERT] Creating UIEvent DRAG at ({x}, {y}), delta=({dx}, {dy})")
            return UIEvent(
                "drag",
                payload={
                    "pos": (x, y),
                    "dx": dx,
                    "dy": dy,
                    **raw_payload
                }
            )
        elif event_type == 'swipe':
            direction = getattr(touch_event, 'direction', 'unknown')
            delta = getattr(touch_event, 'delta', 0)
            logger.info(f"[CONVERT] Creating UIEvent SWIPE direction={direction}, delta={delta}")
            return UIEvent(
                "swipe",
                payload={
                    "direction": direction,
                    "delta": delta,
                    **raw_payload
                }
            )
        else:
            logger.warning(f"[CONVERT] Unrecognized event type: {event_type}")

        return None

    def cleanup(self) -> None:
        """
        Clean up all resources in proper order.

        Order:
        1. Stop main loop
        2. Clean up backend (stop playback)
        3. Clean up UI (renderer, screen manager)
        4. Clean up hardware (touch, framebuffer)
        """
        logger.info("Cleaning up application resources")

        # Stop main loop
        self.running = False

        # Clean up backend first (stop any ongoing operations)
        try:
            if self.backend:
                logger.debug("Shutting down backend")
                self.backend.shutdown()
                self.backend = None
        except Exception as e:
            logger.error(f"Error shutting down backend: {e}", exc_info=True)

        # Clean up UI components
        try:
            if self.screen_manager:
                logger.debug("Cleaning up screen manager")
                # Screen manager doesn't have cleanup but clear reference
                self.screen_manager = None
        except Exception as e:
            logger.error(f"Error cleaning up screen manager: {e}", exc_info=True)

        try:
            if self.renderer:
                logger.debug("Closing renderer")
                self.renderer.close()
                self.renderer = None
        except Exception as e:
            logger.error(f"Error closing renderer: {e}", exc_info=True)

        # Clean up hardware (touch then framebuffer)
        try:
            if self.touch:
                logger.debug("Closing touch controller")
                self.touch.close()
                self.touch = None
        except Exception as e:
            logger.error(f"Error closing touch controller: {e}", exc_info=True)

        try:
            if self.framebuffer:
                logger.debug("Closing framebuffer")
                self.framebuffer.close()
                self.framebuffer = None
        except Exception as e:
            logger.error(f"Error closing framebuffer: {e}", exc_info=True)

        logger.info("Cleanup complete")

    # ------------------------------------------------------------------
    # Touch helpers / status helpers

    def _apply_touch_settings(self) -> None:
        if not self.touch or not self.touch.available:
            return
        cal = self.config.get_touch_calibration()
        if cal:
            self.touch.set_calibration(*cal)
        idx = self.config.get_touch_orientation()
        self.orientation_index = idx % len(ORIENTS)
        orient = ORIENTS[self.orientation_index]
        self.touch.set_orientation(
            swap_xy=orient["SWAP_XY"],
            flip_x=orient["FLIP_X"],
            flip_y=orient["FLIP_Y"],
        )

    def set_touch_orientation(self, index: int) -> None:
        self.orientation_index = index % len(ORIENTS)
        orient = ORIENTS[self.orientation_index]
        if self.touch:
            self.touch.set_orientation(
                swap_xy=orient["SWAP_XY"],
                flip_x=orient["FLIP_X"],
                flip_y=orient["FLIP_Y"],
            )
        self.config.set_touch_orientation(self.orientation_index)
        self.config.save()
        self.set_status(f"Orientation {self.orientation_index + 1}/8 saved", level="info", duration=4)

    def set_touch_calibration(self, calibration: Tuple[int, int, int, int]) -> None:
        self.config.set_touch_calibration(*calibration)
        self.config.save()
        if self.touch:
            self.touch.set_calibration(*calibration)
        self.set_status("Calibration applied", level="success", duration=4)

    def get_touch_orientation(self) -> dict:
        return ORIENTS[self.orientation_index]

    def get_touch_driver_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        if self.touch and getattr(self.touch, "touch", None):
            t = self.touch.touch
            return (t.min_x, t.max_x, t.min_y, t.max_y)
        return None

    def set_status(self, message: str, level: str = "info", duration: float = 3.0) -> None:
        self._status_message = message
        self._status_level = level
        self._status_expiry = time.time() + duration

    def get_status(self) -> Optional[Tuple[str, str]]:
        if not self._status_message:
            return None
        if time.time() > self._status_expiry:
            self._status_message = None
            return None
        return self._status_message, self._status_level


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DFPlayer TFT Touch Application V2")
    parser.add_argument(
        "--fb",
        default="/dev/fb1",
        help="Framebuffer device (default: /dev/fb1)"
    )
    parser.add_argument(
        "--touch",
        default=None,
        help="Touch device path (default: auto-detect)"
    )

    args = parser.parse_args()

    app = DFPlayerTFTApp(fb_device=args.fb, touch_device=args.touch)

    if not app.initialize():
        logger.error("Application initialization failed")
        sys.exit(1)

    app.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
