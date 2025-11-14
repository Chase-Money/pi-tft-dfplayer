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
from typing import Optional

# Ensure the source directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.state_v2 import AppState
from src.backends.dfplayer_v2 import DFPlayerBackend
from src.hardware.framebuffer import Framebuffer
from src.hardware.touch_controller import TouchController
from src.ui.framework_v2.manager import ScreenManagerV2
from src.ui.framework_v2.events import UIEvent
from src.ui.renderer_v2 import FramebufferRendererV2

# Import V2 screens
from src.ui.screens_v2.home import HomeScreen
from src.ui.screens_v2.track_browser import TrackBrowserScreen
from src.ui.screens_v2.now_playing import NowPlayingScreen

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
        fb_device: str = "/dev/fb0",
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

        # Core components (initialized in _init_*)
        self.framebuffer: Optional[Framebuffer] = None
        self.touch: Optional[TouchController] = None
        self.backend: Optional[DFPlayerBackend] = None
        self.state: Optional[AppState] = None
        self.screen_manager: Optional[ScreenManagerV2] = None
        self.renderer: Optional[FramebufferRendererV2] = None

        # Runtime state
        self.running = False

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

            # Initialize hardware
            if not self._init_framebuffer():
                return False
            if not self._init_touch():
                return False

            # Initialize backend
            if not self._init_backend():
                logger.warning("DFPlayer backend initialization failed, continuing anyway")

            # Initialize state
            self._init_state()

            # Initialize UI framework
            self._init_screen_manager()
            self._init_renderer()

            # Register screens
            self._register_screens()

            logger.info("Application initialization complete")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    def _init_framebuffer(self) -> bool:
        """Initialize the framebuffer."""
        try:
            self.framebuffer = Framebuffer(device=self.fb_device)
            logger.info(f"Framebuffer initialized: {self.framebuffer.width}x{self.framebuffer.height}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize framebuffer: {e}")
            return False

    def _init_touch(self) -> bool:
        """Initialize the touch controller."""
        try:
            self.touch = TouchController(device=self.touch_device)
            logger.info("Touch controller initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize touch controller: {e}")
            logger.error("Touch input will not be available")
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

    def _init_state(self) -> None:
        """Initialize application state."""
        # Load mock tracks for testing
        # In production, these would be loaded from track catalog
        mock_tracks = [
            {"number": 1, "title": "Track 001", "artist": "Artist 1"},
            {"number": 2, "title": "Track 002", "artist": "Artist 2"},
            {"number": 3, "title": "Track 003", "artist": "Artist 3"},
            {"number": 4, "title": "Track 004", "artist": "Artist 4"},
            {"number": 5, "title": "Track 005", "artist": "Artist 5"},
        ]

        self.state = AppState(tracks=mock_tracks)
        logger.info(f"State initialized with {len(mock_tracks)} tracks")

    def _init_screen_manager(self) -> None:
        """Initialize the screen manager with services."""
        services = {
            "state": self.state,
            "backend": self.backend,
            "app": self
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
        logger.info("Screens registered: home, track_browser, now_playing")

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
        last_fps_time = time.time()

        try:
            while self.running:
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

            for event in events:
                # Convert touch event to UIEvent
                ui_event = self._touch_to_ui_event(event)
                if ui_event:
                    self.screen_manager.handle_event(ui_event)

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

        if event_type == 'tap':
            return UIEvent(
                "tap",
                payload={
                    "x": touch_event.x,
                    "y": touch_event.y
                }
            )
        elif event_type == 'drag':
            return UIEvent(
                "drag",
                payload={
                    "x": touch_event.x,
                    "y": touch_event.y,
                    "dx": getattr(touch_event, 'dx', 0),
                    "dy": getattr(touch_event, 'dy', 0)
                }
            )
        elif event_type == 'swipe':
            return UIEvent(
                "swipe",
                payload={
                    "direction": touch_event.direction,
                    "delta": getattr(touch_event, 'delta', 0)
                }
            )

        return None

    def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up application resources")

        self.running = False

        try:
            if self.renderer:
                self.renderer.close()
        except Exception as e:
            logger.error(f"Error closing renderer: {e}")

        try:
            if self.framebuffer:
                self.framebuffer.close()
        except Exception as e:
            logger.error(f"Error closing framebuffer: {e}")

        try:
            if self.touch:
                self.touch.close()
        except Exception as e:
            logger.error(f"Error closing touch controller: {e}")

        try:
            if self.backend:
                self.backend.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down backend: {e}")

        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DFPlayer TFT Touch Application V2")
    parser.add_argument(
        "--fb",
        default="/dev/fb0",
        help="Framebuffer device (default: /dev/fb0)"
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
