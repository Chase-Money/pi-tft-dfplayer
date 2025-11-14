"""Touchscreen UI framework runner for the legacy 480x320 display."""

from __future__ import annotations

import time
from typing import Dict, Optional

from PIL import Image, ImageDraw

from ui.framework_v2 import ScreenManagerV2, UIEvent
from ui.screens_v2 import HomeScreen, TrackBrowserScreen, NowPlayingScreen


class TouchscreenFrameworkApp:
    """Bridges DFPlayerApp state with the v2 screen manager."""

    def __init__(self, df_app) -> None:
        self.df_app = df_app
        services = {
            "state": df_app.state,
            "config": df_app.config,
            "app": df_app,
            "tracks": df_app.state.tracks,
        }
        self.manager = ScreenManagerV2(services=services)
        self.manager.register("home", HomeScreen)
        self.manager.register("track_browser", TrackBrowserScreen)
        self.manager.register("now_playing", NowPlayingScreen)
        self.manager.push("home")

        fb = df_app.framebuffer
        self.image = Image.new("RGB", (fb.width, fb.height), (12, 16, 24))
        self.draw = ImageDraw.Draw(self.image)
        self.render_context: Dict[str, object] = {
            "image": self.image,
            "draw": self.draw,
            "fonts": df_app.fonts,
            "state": df_app.state,
        }

    def render(self) -> None:
        fb = self.df_app.framebuffer
        self.manager.render(self.render_context)
        fb.push(self.image)

    def handle_touch(self, px: int, py: int) -> None:
        self.manager.handle_event(UIEvent("tap", {"pos": (px, py)}))

    def handle_drag(self, px: int, py: int, start: tuple[int, int]) -> None:
        self.manager.handle_event(UIEvent("drag", {"pos": (px, py), "start": start}))

    def handle_swipe(self, delta: int) -> None:
        self.manager.handle_event(UIEvent("swipe", {"delta": delta}))
