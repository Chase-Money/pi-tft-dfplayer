"""
Home screen for the Waveshare 128x128 display variant.
"""
from __future__ import annotations
from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..framework.manager import ScreenView
from ..framework.events import UIEvent

class HomeScreenWS(ScreenView):
    name = "home_ws"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.menu_items = ["Browse Tracks", "Now Playing", "Settings"]
        self.selected_index = 0

    def render(self, context: dict) -> None:
        draw: ImageDraw.ImageDraw = context["draw"]
        fonts = context["fonts"]
        
        # Clear screen
        draw.rectangle((0, 0, 128, 128), fill=(0, 0, 0))
        
        # Title
        draw.text((4, 4), "DFPlayer", font=fonts["medium"], fill=(255, 255, 255))
        draw.line((0, 20, 128, 20), fill=(80, 80, 80))

        # Menu items
        for i, item in enumerate(self.menu_items):
            y = 30 + i * 20
            if i == self.selected_index:
                draw.rectangle((0, y - 2, 128, y + 18), fill=(0, 80, 150))
                draw.text((4, y), item, font=fonts["medium"], fill=(255, 255, 255))
            else:
                draw.text((4, y), item, font=fonts["medium"], fill=(200, 200, 200))

    def handle_event(self, event: UIEvent) -> bool:
        if event.type == "swipe":
            delta = event.payload.get("delta", 0)
            self.selected_index = (self.selected_index + delta) % len(self.menu_items)
            return True
        
        if event.type == "tap":
            selected_item = self.menu_items[self.selected_index]
            if selected_item == "Browse Tracks":
                # We'll need to create a 'track_browser_ws' screen next
                # self.manager.push("track_browser_ws")
                print("Navigate to Track Browser (not implemented yet)")
            elif selected_item == "Now Playing":
                self.manager.push("now_playing") # The old one will look bad, but it's a start
            return True
            
        return False
