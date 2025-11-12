"""DFPlayer Mini playback backend.

Implements the PlaybackBackend interface for DFPlayer Mini MP3 module.
"""

import logging
from typing import Optional, Dict, Any

from backends.base import PlaybackBackend
from hardware.dfplayer import DFPlayer

logger = logging.getLogger(__name__)


class DFPlayerBackend(PlaybackBackend):
    """DFPlayer Mini MP3 playback backend.

    Wraps DFPlayer hardware interface with the standard PlaybackBackend API.

    Attributes:
        device: DFPlayer hardware interface
        current_track: Currently playing track number
        volume_level: Current volume level (0-30)
        playing: Playback state
    """

    def __init__(self, port='/dev/serial0', baudrate=9600):
        """Initialize DFPlayer backend.

        Args:
            port: Serial port path
            baudrate: Serial baudrate
        """
        super().__init__(name="DFPlayer")
        self.port = port
        self.baudrate = baudrate
        self.device: Optional[DFPlayer] = None
        self.current_track: Optional[int] = None
        self.volume_level = 18
        self.playing = False

    def initialize(self) -> bool:
        """Initialize DFPlayer hardware.

        Returns:
            bool: True if successful
        """
        try:
            self.device = DFPlayer(self.port, self.baudrate)

            if not self.device.is_connected:
                logger.error("DFPlayer not connected")
                return False

            # Set initial volume
            self.device.set_volume(self.volume_level)

            logger.info("DFPlayer backend initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize DFPlayer backend: {e}")
            return False

    def shutdown(self):
        """Shutdown DFPlayer backend."""
        if self.device:
            try:
                self.device.stop()
                self.device.close()
                logger.info("DFPlayer backend shutdown")
            except Exception as e:
                logger.error(f"Error during DFPlayer shutdown: {e}")

        self.device = None
        self.playing = False

    def play(self):
        """Resume playback."""
        if self.device and self.device.is_connected:
            self.device.play()
            self.playing = True
            logger.debug("DFPlayer: play/resume")

    def pause(self):
        """Pause playback."""
        if self.device and self.device.is_connected:
            self.device.pause()
            self.playing = False
            logger.debug("DFPlayer: pause")

    def stop(self):
        """Stop playback."""
        if self.device and self.device.is_connected:
            self.device.stop()
            self.playing = False
            self.current_track = None
            logger.debug("DFPlayer: stop")

    def next_track(self):
        """Skip to next track."""
        if self.device and self.device.is_connected:
            self.device.next_track()
            self.playing = True
            # Note: We don't track the track number here as DFPlayer handles it
            logger.debug("DFPlayer: next track")

    def prev_track(self):
        """Skip to previous track."""
        if self.device and self.device.is_connected:
            self.device.prev_track()
            self.playing = True
            logger.debug("DFPlayer: previous track")

    def play_track(self, track_number: int):
        """Play specific track by number.

        Args:
            track_number: Track number (1-3000)
        """
        if self.device and self.device.is_connected:
            self.device.play_track(track_number)
            self.current_track = track_number
            self.playing = True
            logger.info(f"DFPlayer: playing track {track_number}")

    def play_folder_track(self, folder: int, track: int):
        """Play track from specific folder.

        Args:
            folder: Folder number (1-99)
            track: Track number within folder (1-255)
        """
        if self.device and self.device.is_connected:
            self.device.play_folder(folder, track)
            self.playing = True
            logger.info(f"DFPlayer: playing folder {folder}, track {track}")

    def set_volume(self, volume: int):
        """Set volume level.

        Args:
            volume: Volume level (0-30)
        """
        volume = max(0, min(30, int(volume)))
        self.volume_level = volume

        if self.device and self.device.is_connected:
            self.device.set_volume(volume)
            logger.debug(f"DFPlayer: volume set to {volume}")

    def get_status(self) -> Dict[str, Any]:
        """Get current playback status.

        Returns:
            dict: Status dictionary with keys:
                - playing: bool
                - track_number: int or None
                - volume: int
                - connected: bool
                - error: str or None
        """
        status = {
            "playing": self.playing,
            "track_number": self.current_track,
            "volume": self.volume_level,
            "connected": self.device.is_connected if self.device else False,
            "error": None
        }

        if self.device and not self.device.is_connected:
            status["error"] = "DFPlayer not connected"

        return status

    @property
    def is_connected(self) -> bool:
        """Check if DFPlayer is connected.

        Returns:
            bool: True if connected
        """
        return self.device is not None and self.device.is_connected
