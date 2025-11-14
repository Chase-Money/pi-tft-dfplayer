#!/usr/bin/env python3
"""
Main application entry point for pi-tft-dfplayer.

Refactored modular version with clean architecture.
"""

import atexit
import logging
import os
import statistics
import sys
import select
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# Hardware modules
from hardware.framebuffer import Framebuffer
from hardware.touch import TouchInput, EVDEV_AVAILABLE

# Core modules
from core.config import get_config
from core.state import get_state, Track
from core.events import get_event_bus, Events

# Backend modules
from backends.dfplayer_backend import DFPlayerBackend

# Utility modules
from utils.metadata import load_metadata, ArtworkCache
from utils.track_catalog import load_track_catalog
from utils.calibration import run_calibration
from ui.app_v2 import TouchscreenFrameworkApp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DFPlayerApp:
    """Main application class."""

    def __init__(self):
        """Initialize application."""
        logger.info("Initializing pi-tft-dfplayer application")

        # Load configuration
        self.config = get_config()
        self.state = get_state()
        self.event_bus = get_event_bus()

        # Hardware initialization
        self.framebuffer = None
        self.touch = None
        self.backend = None

        # UI state
        self.artwork_cache = ArtworkCache(max_size=10)
        self.fonts = self._load_fonts()
        # Register cleanup
        atexit.register(self.cleanup)

    def _load_fonts(self):
        """Load UI fonts."""
        try:
            return {
                'large': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44),
                'medium': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24),
                'small': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18),
            }
        except Exception as e:
            logger.warning(f"Failed to load fonts: {e}, using defaults")
            default = ImageFont.load_default()
            return {'large': default, 'medium': default, 'small': default}

    def initialize_hardware(self):
        """Initialize hardware components."""
        logger.info("Initializing hardware...")

        # Initialize framebuffer
        try:
            self.framebuffer = Framebuffer(device='/dev/fb1')
        except Exception as e:
            logger.error(f"Failed to initialize framebuffer: {e}")
            sys.exit(1)

        # Initialize touch
        self.touch = TouchInput(
            screen_width=self.framebuffer.width,
            screen_height=self.framebuffer.height
        )

        # Load touch settings
        self.touch.set_orientation(self.config.get_touch_orientation())
        cal = self.config.get_touch_calibration()
        if cal:
            self.touch.set_calibration(*cal)

        if not self.touch.is_open and EVDEV_AVAILABLE:
            logger.error("Touch device not initialized. Cannot start application.")
            logger.error("Please check touch device connection and permissions.")
            sys.exit(1)

        # Initialize backend
        self.backend = DFPlayerBackend()
        if not self.backend.initialize():
            logger.warning("DFPlayer backend initialization failed - commands may not work")

        # Set volume from config
        volume = self.config.get_volume()
        self.backend.set_volume(volume)
        self.state.set_volume(volume)

        logger.info("Hardware initialization complete")

    def load_data(self):
        """Load track catalog and metadata."""
        logger.info("Loading data...")

        # Load track catalog
        catalog_path = self.config.get_track_catalog_path()
        tracks = load_track_catalog(catalog_path)
        self.state.set_tracks(tracks)

        # Load metadata
        metadata_path = self.config.get_metadata_path()
        artwork_root = self.config.get_artwork_root()
        metadata = load_metadata(metadata_path, artwork_root)
        self.state.set_metadata(metadata)

        logger.info(f"Loaded {len(tracks)} tracks and {len(metadata)} metadata entries")

    def run_calibration(self):
        """Run touch calibration workflow."""
        logger.info("Starting calibration...")

        cal = run_calibration(self.touch, self.framebuffer, self.fonts['small'])

        if cal:
            self.touch.set_calibration(*cal)
            self.config.set_touch_calibration(*cal)
            self.config.save()
            logger.info("Calibration saved")
        else:
            logger.warning("Calibration cancelled")

    def draw_ui(self, note=None):
        """Draw UI to framebuffer."""
        w, h = self.framebuffer.width, self.framebuffer.height

        # Create canvas
        img = Image.new("RGB", (w, h), (12, 16, 24))
        draw = ImageDraw.Draw(img)

        # Draw main controls
        self._draw_buttons(draw, w, h)
        self._draw_volume(draw)
        self._draw_artwork(img, draw)
        self._draw_track_info(draw)
        self._draw_cal_cfg_buttons(draw, w, h)
        self._draw_track_list(draw, w, h)

        # Draw status note
        if note:
            draw.text((6, h - 22), note, font=self.fonts['small'], fill=(210, 210, 210))

        # Push to framebuffer
        self.framebuffer.push(img)

    def _draw_buttons(self, draw, w, h):
        """Draw playback control buttons."""
        buttons = [
            {"label": "Pause" if self.state.playback.playing else "Play",
             "rect": (20, 24, 200, 86), "fill": (70, 175, 120), "radius": 20},
            {"label": "Stop", "rect": (20, 124, 200, 72), "fill": (195, 80, 80), "radius": 20},
            {"label": "Prev", "rect": (20, 212, 94, 72), "fill": (80, 110, 185), "radius": 16},
            {"label": "Next", "rect": (126, 212, 94, 72), "fill": (80, 110, 185), "radius": 16},
        ]

        for btn in buttons:
            x, y, w, h = btn["rect"]
            draw.rounded_rectangle([x, y, x + w, y + h], radius=btn["radius"], fill=btn["fill"])

            # Center text
            font = self.fonts['large'] if btn["label"] in ("Play", "Pause", "Stop") else self.fonts['medium']
            self._draw_text_center(draw, x, y, w, h, btn["label"], font, (255, 255, 255))

    def _draw_volume(self, draw):
        """Draw volume bar."""
        vx, vy, vw, vh = 20, 292, 200, 20
        vol = self.state.playback.volume

        draw.text((vx, vy - 28), "Volume", font=self.fonts['small'], fill=(215, 215, 215))
        draw.rounded_rectangle([vx, vy, vx + vw, vy + vh], radius=10, fill=(55, 60, 75))

        fillw = int(vw * vol / 30)
        draw.rounded_rectangle([vx, vy, vx + fillw, vy + vh], radius=10, fill=(230, 195, 80))
        draw.text((vx + vw + 8, vy - 4), f"{vol:02d}", font=self.fonts['medium'], fill=(235, 235, 235))

    def _draw_artwork(self, img, draw):
        """Draw album artwork."""
        ax, ay, aw, ah = 260, 20, 200, 200

        draw.rounded_rectangle([ax, ay, ax + aw, ay + ah], radius=18, fill=(32, 34, 46))

        # Get current track
        track = self.state.get_selected_track()
        if not track:
            draw.text((ax + 24, ay + ah // 2 - 10), "No artwork", font=self.fonts['small'], fill=(140, 140, 150))
            return

        # Get artwork from metadata
        meta = self.state.get_track_metadata(track.number)
        artwork_path = meta.get("artwork")

        if artwork_path:
            thumb = self.artwork_cache.get(artwork_path, size=(aw, ah))
            if thumb:
                img.paste(thumb, (ax, ay))
            else:
                draw.text((ax + 24, ay + ah // 2 - 10), "No artwork", font=self.fonts['small'], fill=(140, 140, 150))
        else:
            draw.text((ax + 24, ay + ah // 2 - 10), "No artwork", font=self.fonts['small'], fill=(140, 140, 150))

    def _draw_track_info(self, draw):
        """Draw track information panel."""
        ix, iy, iw, ih = 260, 230, 200, 72

        draw.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=12, fill=(38, 42, 60))

        track = self.state.get_selected_track()
        if not track:
            return

        meta = self.state.get_track_metadata(track.number)
        title = meta.get("title") or track.title or f"Track {track.number:03d}"
        artist = meta.get("artist") or "Unknown Artist"

        # Draw title and artist
        next_y = self._draw_wrapped_text(draw, title, self.fonts['medium'], ix + 12, iy + 8, iw - 24, (235, 235, 235))
        self._draw_wrapped_text(draw, artist, self.fonts['small'], ix + 12, max(next_y, iy + 44), iw - 24, (195, 195, 200))
        draw.text((ix + 12, iy + ih - 24), f"#{track.number:03d}", font=self.fonts['small'], fill=(175, 175, 185))

    def _draw_cal_cfg_buttons(self, draw, w, h):
        """Draw CAL and CFG buttons."""
        cal_rect = (4, 4, 52, 30)
        cfg_rect = (w - 56, 4, 52, 30)

        draw.rounded_rectangle(self._xywh_to_xyxy(cal_rect), radius=6, fill=(90, 90, 140))
        self._draw_text_center(draw, *cal_rect, "CAL", self.fonts['small'], (255, 255, 255))

        draw.rounded_rectangle(self._xywh_to_xyxy(cfg_rect), radius=6, fill=(90, 140, 90))
        self._draw_text_center(draw, *cfg_rect, "CFG", self.fonts['small'], (255, 255, 255))

    def _draw_track_list(self, draw, w, h):
        """Draw scrollable track list."""
        tx, ty, tw, th = 240, 50, max(180, w - 260), max(130, h - 70)

        draw.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=18, fill=(26, 28, 36))
        draw.text((tx + 14, ty + 10), "Tracks", font=self.fonts['medium'], fill=(225, 225, 225))

        # Show now playing
        playing_track = self.state.get_playing_track()
        if playing_track:
            lbl = f"{playing_track.number:03d} {playing_track.title}"
            draw.text((tx + 14, ty + 38), f"Playing: {lbl[:18]}", font=self.fonts['small'], fill=(200, 200, 200))

        # Track list area
        list_x, list_y = tx + 10, ty + 72
        list_w, list_h = max(40, tw - 64), max(24, th - 88)
        row_height = 32

        visible_count = max(1, list_h // row_height)

        # Ensure scroll bounds
        max_scroll = max(0, len(self.state.tracks) - visible_count)
        self.state.track_scroll = max(0, min(self.state.track_scroll, max_scroll))

        # Draw tracks
        for i in range(visible_count):
            idx = self.state.track_scroll + i
            if idx >= len(self.state.tracks):
                break

            track = self.state.tracks[idx]
            row_y = list_y + i * row_height
            row_rect = (list_x, row_y, list_w, row_height - 6)

            fill = (45, 48, 60)
            text_color = (220, 220, 220)
            label = f"{track.number:03d} {track.title}"

            if idx == self.state.playback.now_playing_index:
                fill = (215, 165, 60)
                text_color = (25, 25, 25)
                label = f"▶ {label}"
            elif idx == self.state.playback.selected_track_index:
                fill = (70, 90, 150)

            draw.rounded_rectangle(self._xywh_to_xyxy(row_rect), radius=10, fill=fill)
            self._draw_text_center(draw, *row_rect, label[:22], self.fonts['small'], text_color)

        # Scroll buttons
        scroll_x = list_x + list_w + 8
        up_rect = (scroll_x, list_y, 40, 36)
        down_rect = (scroll_x, list_y + list_h - 36, 40, 36)

        up_active = self.state.track_scroll > 0
        down_active = self.state.track_scroll < max_scroll

        draw.rounded_rectangle(self._xywh_to_xyxy(up_rect),
                                radius=10, fill=(85, 90, 118) if up_active else (52, 56, 72))
        draw.rounded_rectangle(self._xywh_to_xyxy(down_rect),
                                radius=10, fill=(85, 90, 118) if down_active else (52, 56, 72))

        # Draw arrows
        ux, uy, uw, uh = up_rect
        dx, dy, dw, dh = down_rect
        up_color = (235, 235, 235) if up_active else (140, 140, 150)
        down_color = (235, 235, 235) if down_active else (140, 140, 150)

        up_arrow = [(ux + uw / 2, uy + 8), (ux + uw - 10, uy + uh - 8), (ux + 10, uy + uh - 8)]
        down_arrow = [(dx + 10, dy + 8), (dx + dw - 10, dy + 8), (dx + dw / 2, dy + dh - 8)]

        draw.polygon(up_arrow, fill=up_color)
        draw.polygon(down_arrow, fill=down_color)

    def _draw_text_center(self, draw, x, y, w, h, text, font, color=(255, 255, 255)):
        """Draw centered text."""
        x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
        tw, th = x1 - x0, y1 - y0
        draw.text((x + (w - tw) // 2, y + (h - th) // 2), text, font=font, fill=color)

    def _draw_wrapped_text(self, draw, text, font, x, y, max_width, fill, line_spacing=4):
        """Draw wrapped text."""
        if not text:
            return y

        ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (font.size, 0)
        line_height = ascent + descent + line_spacing
        line = ""

        for word in text.split():
            candidate = word if not line else f"{line} {word}"

            try:
                width = draw.textlength(candidate, font=font)
            except AttributeError:
                x0, _, x1, _ = draw.textbbox((0, 0), candidate, font=font)
                width = x1 - x0

            if width <= max_width or not line:
                line = candidate
            else:
                draw.text((x, y), line, font=font, fill=fill)
                y += line_height
                line = word

        if line:
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height

        return y

    def _xywh_to_xyxy(self, rect):
        """Convert (x, y, w, h) to (x, y, x+w, y+h)."""
        x, y, w, h = rect
        return [x, y, x + w, y + h]

    def _inside(self, rect, px, py):
        """Check if point is inside rectangle."""
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h

    def handle_touch(self, px, py):
        """Handle touch event at screen coordinates."""
        w, h = self.framebuffer.width, self.framebuffer.height

        # CAL button
        if self._inside((4, 4, 52, 30), px, py):
            self.run_calibration()
            self.draw_ui("Calibrated")
            return

        # CFG button (cycle orientation)
        if self._inside((w - 56, 4, 52, 30), px, py):
            new_idx = self.touch.cycle_orientation()
            self.config.set_touch_orientation(new_idx)
            self.config.save()
            self.draw_ui(f"Orientation {new_idx + 1}/8")
            return

        # Playback buttons
        if self._inside((20, 24, 200, 86), px, py):  # Play/Pause
            if self.state.playback.playing:
                self.backend.pause()
                self.state.pause_playback()
                self.draw_ui("Paused")
            else:
                track = self.state.get_selected_track()
                if track:
                    self.backend.play_track(track.number)
                    self.state.start_playback()
                    self.draw_ui(f"Playing {track.title}")
            return

        if self._inside((20, 124, 200, 72), px, py):  # Stop
            self.backend.stop()
            self.state.stop_playback()
            self.draw_ui("Stopped")
            return

        if self._inside((20, 212, 94, 72), px, py):  # Prev
            new_track = self.state.advance_track(-1)
            if new_track:
                self.backend.play_track(new_track.number)
                self.state.start_playback()
                self.draw_ui(f"Playing {new_track.title}")
            return

        if self._inside((126, 212, 94, 72), px, py):  # Next
            new_track = self.state.advance_track(1)
            if new_track:
                self.backend.play_track(new_track.number)
                self.state.start_playback()
                self.draw_ui(f"Playing {new_track.title}")
            return

        # Track list scroll and selection
        self._handle_track_list_touch(px, py, w, h)

    def _handle_track_list_touch(self, px, py, w, h):
        """Handle touch in track list area."""
        tx, ty, tw, th = 240, 50, max(180, w - 260), max(130, h - 70)
        list_x, list_y = tx + 10, ty + 72
        list_w, list_h = max(40, tw - 64), max(24, th - 88)

        scroll_x = list_x + list_w + 8
        up_rect = (scroll_x, list_y, 40, 36)
        down_rect = (scroll_x, list_y + list_h - 36, 40, 36)

        # Scroll up
        if self._inside(up_rect, px, py) and self.state.track_scroll > 0:
            self.state.track_scroll -= 1
            self.draw_ui()
            return

        # Scroll down
        visible_count = max(1, list_h // 32)
        max_scroll = max(0, len(self.state.tracks) - visible_count)

        if self._inside(down_rect, px, py) and self.state.track_scroll < max_scroll:
            self.state.track_scroll += 1
            self.draw_ui()
            return

        # Track selection
        if self._inside((list_x, list_y, list_w, list_h), px, py):
            row = (py - list_y) // 32
            idx = self.state.track_scroll + int(row)

            if 0 <= idx < len(self.state.tracks):
                track = self.state.select_track_index(idx)
                self.backend.play_track(track.number)
                self.state.start_playback(idx)
                self.draw_ui(f"Playing {track.title}")

    def update_volume_from_x(self, px):
        """Update volume from X coordinate."""
        vx, vy, vw, vh = 20, 292, 200, 20
        clamped = max(vx, min(vx + vw, px))
        new_vol = int((clamped - vx) * 30 / vw)
        new_vol = max(0, min(30, new_vol))

        if new_vol != self.state.playback.volume:
            self.state.set_volume(new_vol)
            self.backend.set_volume(new_vol)
            self.config.set_volume(new_vol)
            self.draw_ui()

    def main_loop(self):
        """Main event loop."""
        if not self.touch.is_open:
            logger.error("Touch device not available - cannot run main loop")
            return

        logger.info("Entering main loop")

        if self.state.tracks:
            self.state.select_track_index(0)

        self.draw_ui()

        if not EVDEV_AVAILABLE:
            logger.error("evdev not available - exiting")
            return

        touching = False
        drag_vol = False
        raw_bufx, raw_bufy = [], []
        touch_last = None
        last_drag = 0.0

        from evdev import ecodes

        fd = self.touch.fileno()

        try:
            while True:
                self._drain_backend_events()
                try:
                    rlist, _, _ = select.select([fd], [], [], 0.05)
                except (OSError, ValueError):
                    continue

                if not rlist:
                    continue

                while True:
                    ev = self.touch.read_event()
                    if ev is None:
                        break

                    if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                        touching = (ev.value == 1)
                        if touching:
                            raw_bufx.clear()
                            raw_bufy.clear()
                            touch_last = None
                            drag_vol = False
                        else:
                            if not drag_vol and touch_last:
                                self.handle_touch(*touch_last)
                                touch_last = None
                            raw_bufx.clear()
                            raw_bufy.clear()
                    elif ev.type == ecodes.EV_ABS:
                        if ev.code == ecodes.ABS_X:
                            raw_bufx.append(ev.value)
                        elif ev.code == ecodes.ABS_Y:
                            raw_bufy.append(ev.value)
                        else:
                            continue

                        if touching and len(raw_bufx) >= 4 and len(raw_bufy) >= 4:
                            med_rx = int(statistics.median(raw_bufx[-6:]))
                            med_ry = int(statistics.median(raw_bufy[-6:]))
                            px, py = self.touch.scale_xy(med_rx, med_ry)
                            touch_last = (px, py)

                            if not drag_vol and self._inside((20, 292, 200, 20), px, py):
                                drag_vol = True

                            if drag_vol:
                                now = time.time()
                                if now - last_drag > 0.02:
                                    self.update_volume_from_x(px)
                                    last_drag = now
                if touch_last and not touching and not drag_vol:
                    self.handle_touch(*touch_last)
                    touch_last = None
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")

        try:
            if self.backend:
                self.backend.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down backend: {e}")

        try:
            if self.framebuffer:
                self.framebuffer.clear((0, 0, 0))
                self.framebuffer.close()
        except Exception as e:
            logger.warning(f"Error closing framebuffer: {e}")

        try:
            if self.touch:
                self.touch.close()
        except Exception as e:
            logger.warning(f"Error closing touch: {e}")

        logger.info("Cleanup complete")

    def _drain_backend_events(self):
        if not self.backend:
            return
        while True:
            event = self.backend.poll_event(timeout=0)
            if not event:
                break
            etype = event.get("type")
            if etype == "track_finished":
                track = self.state.advance_track(1)
                if track:
                    logger.info(f"Auto-advancing to {track.title}")
                    self.backend.play_track(track.number)
                    self.state.start_playback()
                    self.draw_ui(f"Playing {track.title}")
                else:
                    logger.info("No more tracks to auto-advance")
            elif etype == "track_started":
                logger.info(f"DFPlayer confirmed track {event.get('track')}")
            elif etype == "error":
                code = event.get("code")
                logger.error(f"DFPlayer reported error 0x{code:02x}")

    def run_framework_ui(self):
        """Run the experimental v2 screen-manager UI."""
        if self.touch is None or not self.touch.is_open:
            logger.error("Touch device not initialized. Cannot start v2 UI")
            return

        ui_app = TouchscreenFrameworkApp(self)
        ui_app.render()

        from evdev import ecodes

        fd = self.touch.fileno()
        touching = False
        raw_bufx, raw_bufy = [], []
        touch_last = None

        while True:
            self._drain_backend_events()
            try:
                rlist, _, _ = select.select([fd], [], [], 0.05)
            except (OSError, ValueError):
                continue

            if not rlist:
                continue

            while True:
                ev = self.touch.read_event()
                if ev is None:
                    break
                if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                    touching = (ev.value == 1)
                    if touching:
                        raw_bufx.clear()
                        raw_bufy.clear()
                        touch_last = None
                    else:
                        if touch_last:
                            ui_app.handle_touch(*touch_last)
                            ui_app.render()
                            touch_last = None
                elif ev.type == ecodes.EV_ABS:
                    if ev.code == ecodes.ABS_X:
                        raw_bufx.append(ev.value)
                    elif ev.code == ecodes.ABS_Y:
                        raw_bufy.append(ev.value)

                    if touching and len(raw_bufx) >= 4 and len(raw_bufy) >= 4:
                        med_rx = int(statistics.median(raw_bufx[-6:]))
                        med_ry = int(statistics.median(raw_bufy[-6:]))
                        px, py = self.touch.scale_xy(med_rx, med_ry)
                        touch_last = (px, py)



def main():
    """Main entry point."""
    use_framework = os.environ.get("DFPLAYER_UI_FRAMEWORK") == "1"
    if use_framework:
        try:
            logger.info("DFPLAYER_UI_FRAMEWORK=1 → launching ScreenManagerV2 application")
            from app_v2 import Application

            Application().run()
            return
        except Exception as exc:
            logger.error("Failed to run v2 application, falling back to legacy UI: %s", exc, exc_info=True)

    app = DFPlayerApp()

    try:
        app.initialize_hardware()
        app.load_data()
        app.main_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
