"""DFPlayer Mini playback backend (v2).

Revised to use absolute hardware import to avoid top-level relative import issues.
"""

import logging
from typing import Optional, Dict, Any

from .base import PlaybackBackend
from hardware.dfplayer import DFPlayer

logger = logging.getLogger(__name__)


class DFPlayerBackendV2(PlaybackBackend):
    """DFPlayer Mini MP3 playback backend (v2)."""

    def __init__(self, port='/dev/serial0', baudrate=9600):
        super().__init__(name="DFPlayer")
        self.port = port
        self.baudrate = baudrate
        self.device: Optional[DFPlayer] = None
        self.current_track: Optional[int] = None
        self.volume_level = 18
        self.playing = False

    def initialize(self) -> bool:
        try:
            self.device = DFPlayer(self.port, self.baudrate)
            if not self.device.is_connected:
                logger.error("DFPlayer not connected")
                return False
            self.device.set_volume(self.volume_level)
            logger.info("DFPlayer backend initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DFPlayer: {e}")
            return False

    # PlaybackBackend API
    def play_track(self, track_number: int) -> bool:
        if not self.device:
            return False
        try:
            self.device.play_track(track_number)
            self.current_track = track_number
            self.playing = True
            return True
        except Exception as e:
            logger.error(f"play_track failed: {e}")
            return False

    def pause(self) -> bool:
        if not self.device:
            return False
        try:
            self.device.pause()
            self.playing = False
            return True
        except Exception as e:
            logger.error(f"pause failed: {e}")
            return False

    def stop(self) -> bool:
        if not self.device:
            return False
        try:
            self.device.stop()
            self.playing = False
            return True
        except Exception as e:
            logger.error(f"stop failed: {e}")
            return False

    def next(self) -> bool:
        if not self.device:
            return False
        try:
            self.device.next()
            self.playing = True
            return True
        except Exception as e:
            logger.error(f"next failed: {e}")
            return False

    def previous(self) -> bool:
        if not self.device:
            return False
        try:
            self.device.previous()
            self.playing = True
            return True
        except Exception as e:
            logger.error(f"previous failed: {e}")
            return False

    def set_volume(self, level: int) -> bool:
        if not self.device:
            self.volume_level = level
            return False
        try:
            self.device.set_volume(level)
            self.volume_level = level
            return True
        except Exception as e:
            logger.error(f"set_volume failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "playing": self.playing,
            "volume": self.volume_level,
            "current_track": self.current_track,
        }

    def shutdown(self) -> None:
        try:
            if self.device:
                self.device.stop()
        except Exception:
            pass

