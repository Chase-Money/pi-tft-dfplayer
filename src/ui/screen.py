"""
UI screen rendering for the DFPlayer GUI.
"""

from PIL import Image, ImageDraw, ImageFont

class Screen:
    def __init__(self, width, height, framebuffer):
        self.width = width
        self.height = height
        self.framebuffer = framebuffer
        self.image = Image.new("RGB", (self.width, self.height), (12, 16, 24))
        self.draw = ImageDraw.Draw(self.image)
        self.load_fonts()

    def load_fonts(self):
        """Load fonts for the UI."""
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except Exception:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def render(self, state, components, metadata_manager):
        """Render the UI based on the application state."""
        # Clear the screen
        self.draw.rectangle((0, 0, self.width, self.height), fill=(12, 16, 24))

        # Draw components
        for component in components.values():
            if isinstance(component, VolumeSlider):
                component.draw(self.draw, state.volume, self.font_medium)
            elif isinstance(component, Button):
                component.draw(self.draw, self.font_large, state)

        # Draw track list
        self.draw_track_list(state)

        # Draw artwork and metadata
        self.draw_artwork_and_metadata(state, metadata_manager)

        # Push to framebuffer
        self.framebuffer.push(self.image)

    def draw_artwork_and_metadata(self, state, metadata_manager):
        """Draw the artwork and metadata panel."""
        ART_RECT = (260, 20, 200, 200)
        INFO_RECT = (260, 230, 200, 72)

        # Artwork
        artwork = metadata_manager.get_artwork(state.current_track_number, (ART_RECT[2], ART_RECT[3]))
        if artwork:
            self.image.paste(artwork, (ART_RECT[0], ART_RECT[1]))
        else:
            self.draw.rounded_rectangle(ART_RECT, radius=18, fill=(32, 34, 46))
            self.draw_text_center(ART_RECT, "No artwork", self.font_small, color=(140, 140, 150))

        # Metadata
        self.draw.rounded_rectangle(INFO_RECT, radius=12, fill=(38, 42, 60))
        metadata = metadata_manager.get_metadata(state.current_track_number)
        title = metadata.get("title") or f"Track {state.current_track_number:04d}"
        artist = metadata.get("artist") or "Unknown Artist"

        self.draw_wrapped_text(title, self.font_medium, INFO_RECT[0] + 12, INFO_RECT[1] + 8, INFO_RECT[2] - 24, fill=(235, 235, 235))
        self.draw_wrapped_text(artist, self.font_small, INFO_RECT[0] + 12, INFO_RECT[1] + 44, INFO_RECT[2] - 24, fill=(195, 195, 200))
        self.draw.text((INFO_RECT[0] + 12, INFO_RECT[1] + INFO_RECT[3] - 24), f"#{state.current_track_number:04d}", font=self.font_small, fill=(175, 175, 185))

    def draw_calibration_target(self, x, y):
        """Draw a calibration target on the screen."""
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 0))
        self.draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 255, 0))
        self.draw.line((x - 20, y, x + 20, y), fill=(255, 255, 0))
        self.draw.line((x, y - 20, x, y + 20), fill=(255, 255, 0))
        self.draw.text((10, self.height - 24), "Tap target (hold ~0.5s)...", font=self.font_small, fill=(220, 220, 220))
        self.framebuffer.push(self.image)

    def draw_track_list(self, state):
        """Draw the track list panel."""
        TRACK_PANEL = (240, 50, max(180, self.width - 260), max(130, self.height - 70))
        TRACK_HEADER_HEIGHT = 44
        TRACK_ROW_HEIGHT = 32
        TRACK_SCROLL_BTN_W = 40

        tx, ty, tw, th = TRACK_PANEL
        self.draw.rounded_rectangle((tx, ty, tx + tw, ty + th), radius=18, fill=(26, 28, 36))
        self.draw.text((tx + 14, ty + 10), "Tracks", font=self.font_medium, fill=(225, 225, 225))

        list_x = tx + 10
        list_y = ty + TRACK_HEADER_HEIGHT
        list_w = max(40, tw - TRACK_SCROLL_BTN_W - 24)
        list_h = max(24, th - TRACK_HEADER_HEIGHT - 16)
        
        scroll_x = list_x + list_w + 8
        up_rect = (scroll_x, list_y, TRACK_SCROLL_BTN_W, 36)
        down_rect = (scroll_x, list_y + list_h - 36, TRACK_SCROLL_BTN_W, 36)

        if state.tracks:
            visible_rows = list_h // TRACK_ROW_HEIGHT
            
            for i in range(visible_rows):
                track_index = state.track_scroll_position + i
                if track_index >= len(state.tracks):
                    break
                
                track = state.tracks[track_index]
                row_y = list_y + i * TRACK_ROW_HEIGHT
                row_rect = (list_x, row_y, list_w, TRACK_ROW_HEIGHT - 6)
                
                fill_color = (45, 48, 60)
                text_color = (220, 220, 220)

                if track_index == state.now_playing_index:
                    fill_color = (215, 165, 60)
                    text_color = (25, 25, 25)
                elif track_index == state.selected_track_index:
                    fill_color = (70, 90, 150)

                self.draw.rounded_rectangle((row_rect[0], row_rect[1], row_rect[0] + row_rect[2], row_rect[1] + row_rect[3]), radius=10, fill=fill_color)
                
                label = f'{track["number"]:03d} {track["title"]}'
                if track_index == state.now_playing_index:
                    label = f"▶ {label}"
                
                self.draw_text_center(row_rect, label, self.font_small, color=text_color)
        else:
            self.draw.text((tx + 14, ty + 50), "No tracks found", font=self.font_small, fill=(210, 210, 210))

        # Draw scroll buttons
        up_fill = (85,90,118) if state.track_scroll_position > 0 else (52,56,72)
        down_fill = (85,90,118) if state.track_scroll_position < len(state.tracks) - (list_h // TRACK_ROW_HEIGHT) else (52,56,72)
        up_color = (235,235,235) if state.track_scroll_position > 0 else (140,140,150)
        down_color = (235,235,235) if state.track_scroll_position < len(state.tracks) - (list_h // TRACK_ROW_HEIGHT) else (140,140,150)
        
        self.draw.rounded_rectangle(up_rect, radius=10, fill=up_fill)
        self.draw.rounded_rectangle(down_rect, radius=10, fill=down_fill)
        
        ux, uy, uw, uh = up_rect
        dx, dy, dw, dh = down_rect
        up_arrow = [(ux + uw/2, uy + 8), (ux + uw - 10, uy + uh - 8), (ux + 10, uy + uh - 8)]
        down_arrow = [(dx + 10, dy + 8), (dx + dw - 10, dy + 8), (dx + dw/2, dy + dh - 8)]
        self.draw.polygon(up_arrow, fill=up_color)
        self.draw.polygon(down_arrow, fill=down_color)


    def draw_text_center(self, rect, text, font, color=(255, 255, 255)):
        """Draw text centered in a rectangle."""
        x, y, w, h = rect
        text_bbox = self.draw.textbbox((0, 0), text, font=font)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        self.draw.text((x + (w - tw) // 2, y + (h - th) // 2), text, font=font, fill=color)
