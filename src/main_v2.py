#!/usr/bin/env python3
"""
Legacy entry point (v2 era) with profile selection.

Canonical runtime entry is `src/main.py` (app_v2 + ConfigV2 + ScreenManagerV2).
This file is retained for compatibility only; do not add new features here.
"""

import atexit
import logging
import os
import sys
import time
from typing import Any
try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - allow import without PIL in dev envs
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore
    PIL_AVAILABLE = False

from core.config import get_config
from core.state import get_state
from core.events import get_event_bus

try:
    from core.hardware_profile import detect_profile, select_hardware, import_by_path  # type: ignore
except Exception:  # pragma: no cover - fallback if v3 not available
    from core.profile_select_v2 import detect_profile, select_hardware, import_by_path  # type: ignore
from utils.metadata import load_metadata, ArtworkCache
from utils.track_catalog import load_track_catalog
from backends.dfplayer_v2 import DFPlayerBackend as DFPlayerBackendV2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DFPlayerAppV2:
    def __init__(self, cli_hardware: str | None = None) -> None:
        self.config = get_config()
        self.state = get_state()
        self.event_bus = get_event_bus()
        self.artwork_cache = ArtworkCache(max_size=6)
        self.fonts = self._load_fonts()

        self.display: Any = None
        self.input: Any = None
        self.backend = None
        self.cli_hardware = cli_hardware
        self.profile = detect_profile(cli_arg=self.cli_hardware, env=os.environ, config=self.config)
        self.variant = "unknown"

        atexit.register(self.cleanup)

    def _load_fonts(self):
        if not PIL_AVAILABLE:
            return {'large': None, 'medium': None, 'small': None}  # type: ignore
        try:
            return {
                'large': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12),
                'medium': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10),
                'small': ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8),
            }
        except Exception:
            default = ImageFont.load_default()
            return {'large': default, 'medium': default, 'small': default}

    def initialize(self) -> None:
        # Hardware selection
        disp_path, input_path = select_hardware(self.profile)
        DispClass = import_by_path(disp_path)
        InputClass = import_by_path(input_path)
        self.variant = "st7735_buttons" if "display_st7735" in disp_path else "ili9486_touch"

        # Prefer emulator in non-Pi envs for variant display
        use_emul = os.environ.get("DFPLAYER_USE_EMULATOR") == "1"
        display_kwargs = {"use_emulator": use_emul} if self.variant == "st7735_buttons" else {}
        self.display = DispClass(**display_kwargs)

        self.input = InputClass()

        # Backend
        self.backend = DFPlayerBackendV2()
        self.backend.initialize()
        vol = self.config.get_volume()
        self.backend.set_volume(vol)
        self.state.set_volume(vol)

        # Data
        tracks = load_track_catalog(self.config.get_track_catalog_path())
        self.state.set_tracks(tracks)
        metadata = load_metadata(self.config.get_metadata_path(), self.config.get_artwork_root())
        self.state.set_metadata(metadata)

        if self.state.tracks:
            self.state.select_track_index(0)

        # Wire input if buttons
        if "button_input" in input_path:
            self._wire_buttons()

    def _wire_buttons(self) -> None:
        from hardware.button_input import Button, ButtonEvent

        bi = self.input
        bi.register_callback(Button.KEY1, ButtonEvent.PRESS, self._toggle_play)
        bi.register_callback(Button.KEY2, ButtonEvent.PRESS, self._stop)
        bi.register_callback(Button.KEY3, ButtonEvent.PRESS, self._noop)
        bi.register_callback(Button.UP, ButtonEvent.PRESS, lambda: self._advance_track(-1))
        bi.register_callback(Button.DOWN, ButtonEvent.PRESS, lambda: self._advance_track(1))
        bi.register_callback(Button.LEFT, ButtonEvent.PRESS, lambda: self._adjust_volume(-1))
        bi.register_callback(Button.RIGHT, ButtonEvent.PRESS, lambda: self._adjust_volume(1))
        bi.register_callback(Button.PRESS, ButtonEvent.PRESS, self._play_selected)

        # Holds for next/prev
        bi.register_callback(Button.KEY1, ButtonEvent.HOLD, lambda: self._advance_track(1))
        bi.register_callback(Button.KEY2, ButtonEvent.HOLD, lambda: self._advance_track(-1))

    # --- Button handlers ---
    def _toggle_play(self):
        if self.state.playback.playing:
            self.backend.pause()
            self.state.pause_playback()
        else:
            tr = self.state.get_selected_track()
            if tr:
                self.backend.play_track(tr.number)
                self.state.start_playback()
        self.draw()

    def _stop(self):
        self.backend.stop()
        self.state.stop_playback()
        self.draw()

    def _advance_track(self, delta: int):
        tr = self.state.advance_track(delta)
        if tr:
            self.backend.play_track(tr.number)
            self.state.start_playback()
        self.draw()

    def _adjust_volume(self, delta: int):
        new_vol = max(0, min(30, self.state.playback.volume + delta))
        if new_vol != self.state.playback.volume:
            self.state.set_volume(new_vol)
            self.backend.set_volume(new_vol)
            self.config.set_volume(new_vol)
        self.draw()

    def _play_selected(self):
        tr = self.state.get_selected_track()
        if tr:
            self.backend.play_track(tr.number)
            self.state.start_playback()
        self.draw()

    def _noop(self):
        self.draw()

    # --- Rendering ---
    def draw(self):
        # Decide minimal layout
        if not self.display:
            return
        if self.variant == "st7735_buttons":
            self._draw_128()
        else:
            # Fallback: draw nothing here; legacy UI remains in src/main.py
            return

    def _draw_128(self) -> None:
        if not PIL_AVAILABLE:
            return
        from ui.views_v2 import (
            draw_play_indicator,
            draw_track_number,
            draw_artwork_panel,
            draw_title_line,
            draw_volume_bar,
        )

        img = Image.new("RGB", (128, 128), (12, 16, 24))
        d = ImageDraw.Draw(img)

        tr = self.state.get_selected_track()
        title = tr.title if tr else "No Track"
        number = tr.number if tr else 0

        # Play indicator + track number
        draw_play_indicator(d, self.state.playback.playing, (4, 4), self.fonts['medium'])
        draw_track_number(d, number, (28, 6), self.fonts['medium'])

        # Artwork panel 64x64
        art = self.state.get_track_metadata(number).get("artwork") if tr else None
        draw_artwork_panel(img, d, art, (32, 24, 64, 64))

        # Title line and volume bar
        draw_title_line(d, title, (4, 96), self.fonts['small'])
        draw_volume_bar(d, self.state.playback.volume, (4, 118, 120, 6))

        self.display.push(img)

    def run(self):
        if hasattr(self.input, 'poll') and callable(self.input.poll):
            # Polling loop at ~100 Hz
            logger.info("Entering main loop (polling)")
            self.draw()
            try:
                while True:
                    self.input.poll()
                    time.sleep(0.01)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
        else:
            logger.info("No input poll loop available; exiting")

    def cleanup(self) -> None:
        try:
            if self.display and hasattr(self.display, 'clear'):
                self.display.clear((0, 0, 0))
            if self.display and hasattr(self.display, 'close'):
                self.display.close()
        except Exception:
            pass
        try:
            if self.input and hasattr(self.input, 'cleanup'):
                self.input.cleanup()
        except Exception:
            pass
        try:
            if self.backend:
                self.backend.shutdown()
        except Exception:
            pass


def main():
    # Lightweight CLI flag for hardware profile override
    import argparse
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--hardware", dest="hardware", default=None, help="Hardware profile (e.g. st7735_buttons, ili9486_touch)")
    args, _ = parser.parse_known_args()

    app = DFPlayerAppV2(cli_hardware=args.hardware)
    try:
        app.initialize()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
