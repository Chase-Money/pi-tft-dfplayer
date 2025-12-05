"""
Main application class for the Waveshare 1.44" LCD HAT variant.
"""
import time
import sys
import os
import statistics
import logging
from PIL import Image, ImageDraw, ImageFont

from .core.state import ApplicationState, get_state

# For backward compatibility with existing code, alias the new class
AppState = ApplicationState
from .backends.dfplayer_backend import DFPlayerBackend
from .hardware.display_st7735 import DisplayST7735
from .hardware.button_input import ButtonInput, Button, ButtonEvent
from .ui.framework.manager import ScreenManagerV2
from .ui.framework.events import UIEvent

logger = logging.getLogger(__name__)

# Import the new simplified screens (we will create these next)
# For now, let's use the old screens and see how they break
from .ui.screens_waveshare.home_ws import HomeScreenWS
from .ui.screens.track_browser import TrackBrowserScreen
from .ui.screens.now_playing import NowPlayingScreen


class ApplicationWaveshare:
    """The main application orchestrator for the Waveshare hardware."""

    def __init__(self):
        self._init_display()
        self._init_input()
        self._load_resources()

        # Initialize State and Services
        mock_tracks = [
            {"number": 1, "title": "First Song", "artist": "Artist A"},
            {"number": 2, "title": "Second Song", "artist": "Artist B"},
            {"number": 3, "title": "Third Song", "artist": "Artist C"},
        ]
        self.state = AppState(tracks=mock_tracks)
        self.backend = DFPlayerBackend()
        if not self.backend.initialize():
            logger.warning("DFPlayer backend could not be initialized.")
        
        services = {
            "state": self.state,
            "app": self,
            "backend": self.backend,
        }

        # Initialize Screen Manager
        self.screen_manager = ScreenManagerV2(services)
        self.screen_manager.register("home", HomeScreenWS)
        self.screen_manager.register("track_browser", TrackBrowserScreen)
        self.screen_manager.register("now_playing", NowPlayingScreen)

    def _init_display(self):
        """Initializes the ST7735 display."""
        self.display = DisplayST7735()
        self.image = Image.new("RGB", (self.display.width, self.display.height), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def _init_input(self):
        """Initializes the button input."""
        self.input = ButtonInput()
        self.input.register_callback(Button.UP, ButtonEvent.PRESS, lambda: self.handle_button("UP"))
        self.input.register_callback(Button.DOWN, ButtonEvent.PRESS, lambda: self.handle_button("DOWN"))
        self.input.register_callback(Button.LEFT, ButtonEvent.PRESS, lambda: self.handle_button("LEFT"))
        self.input.register_callback(Button.RIGHT, ButtonEvent.PRESS, lambda: self.handle_button("RIGHT"))
        self.input.register_callback(Button.PRESS, ButtonEvent.PRESS, lambda: self.handle_button("PRESS"))
        self.input.register_callback(Button.KEY1, ButtonEvent.PRESS, lambda: self.handle_button("KEY1"))
        self.input.register_callback(Button.KEY2, ButtonEvent.PRESS, lambda: self.handle_button("KEY2"))
        self.input.register_callback(Button.KEY3, ButtonEvent.PRESS, lambda: self.handle_button("KEY3"))

    def _load_resources(self):
        """Loads fonts, scaling them for the small screen."""
        self.fonts = {
            "large": ImageFont.load_default(),
            "medium": ImageFont.load_default(),
            "small": ImageFont.load_default(),
        }
        try:
            self.fonts["large"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            self.fonts["medium"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
            self.fonts["small"] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except IOError:
            logger.warning("Default fonts used. For better display, install DejaVu fonts.")

    def handle_button(self, button_name: str):
        """Maps a hardware button press to a UIEvent."""
        event = None
        if button_name in ["UP", "DOWN"]:
            # Map to swipe for list navigation
            event = UIEvent("swipe", payload={"delta": -1 if button_name == "UP" else 1})
        elif button_name == "PRESS":
            # Map to tap for selection
            # TODO: The framework doesn't currently support tap events without coordinates.
            # Button-based UIs need to send tap events with dummy coordinates (e.g., x=0, y=0)
            # or the framework needs to support coordinate-less taps. For now, sending a
            # generic tap which may not be fully compatible with all widgets expecting
            # positional data. Consider adding support for centerpoint taps or making
            # widgets handle missing coordinates gracefully.
            event = UIEvent("tap", payload={"x": 0, "y": 0})  # Dummy coordinates
        elif button_name == "KEY1": # Use as a 'Back' button
             self.screen_manager.pop()
        
        if event:
            self.screen_manager.handle_event(event)

    def run(self):
        """Main application loop."""
        self.screen_manager.push("home")

        while True:
            self.input.poll() # Poll for button presses
            self.render()
            self.display.push(self.image)
            time.sleep(0.02) # 50fps

    def render(self):
        """Renders the current screen."""
        context = {
            "image": self.image,
            "draw": self.draw,
            "fonts": self.fonts,
            "state": self.state,
        }
        self.screen_manager.render(context)

    def cleanup(self):
        """Cleans up resources."""
        if self.backend:
            self.backend.cleanup()
        if self.input:
            self.input.cleanup()
        if self.display:
            self.display.close()
        logger.info("Application cleaned up.")

if __name__ == "__main__":
    app = None
    try:
        app = ApplicationWaveshare()
        app.run()
    except KeyboardInterrupt:
        logger.info("Exiting application.")
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}")
        sys.exit(1)
    finally:
        if app:
            app.cleanup()
