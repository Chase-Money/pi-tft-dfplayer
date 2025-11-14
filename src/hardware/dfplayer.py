"""DFPlayer Mini UART interface module.

Handles serial communication with the DFPlayer Mini MP3 module over UART.
Implements the DFPlayer command protocol with checksums and error handling.
"""

import logging
from typing import Optional
import serial

logger = logging.getLogger(__name__)


class DFPlayer:
    """DFPlayer Mini serial interface.

    Manages UART communication with DFPlayer Mini module using a custom
    10-byte packet protocol with checksum validation.

    Attributes:
        port: Serial port path (default: /dev/serial0)
        baudrate: Communication speed (default: 9600)
        timeout: Serial read timeout in seconds

    Example:
        >>> with DFPlayer('/dev/serial0') as player:
        ...     player.set_volume(20)
        ...     player.play_track(1)

    Note:
        DFPlayer Mini expects files organized as /mp3/0001.mp3, /mp3/0002.mp3
        on its micro-SD card. Track numbers must match filesystem numbering.
    """

    # Command constants
    CMD_NEXT = 0x01
    CMD_PREV = 0x02
    CMD_PLAY_TRACK = 0x03
    CMD_VOLUME_SET = 0x06
    CMD_PLAY = 0x0D
    CMD_PAUSE = 0x0E
    CMD_PLAY_FOLDER = 0x0F
    CMD_STOP = 0x16

    # Valid ranges
    MIN_VOLUME = 0
    MAX_VOLUME = 30
    MIN_TRACK = 1
    MAX_TRACK = 3000
    MIN_FOLDER = 1
    MAX_FOLDER = 99

    def __init__(self, port: str = '/dev/serial0', baudrate: int = 9600, timeout: float = 0.1) -> None:
        """Initialize DFPlayer interface.

        Args:
            port: Serial port path
            baudrate: Communication baudrate (typically 9600)
            timeout: Serial read timeout in seconds

        Raises:
            ValueError: If port is empty or parameters are invalid
            serial.SerialException: If serial port cannot be opened
            PermissionError: If insufficient permissions to access port
        """
        if not port or not isinstance(port, str):
            raise ValueError("Port must be a non-empty string")
        if baudrate <= 0:
            raise ValueError(f"Baudrate must be positive, got {baudrate}")
        if timeout < 0:
            raise ValueError(f"Timeout must be non-negative, got {timeout}")

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._connect()

    def _connect(self) -> None:
        """Establish serial connection with error handling.

        Sets self._ser to None if connection fails, allowing graceful degradation.
        """
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"DFPlayer connected on {self.port} at {self.baudrate} baud")
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            logger.error("DFPlayer commands will not work. Check connection and cable.")
            self._ser = None
        except PermissionError as e:
            logger.error(f"Permission denied accessing {self.port}: {e}")
            logger.error("Try: sudo usermod -a -G dialout $USER")
            self._ser = None
        except Exception as e:
            logger.error(f"Unexpected error initializing serial: {e}")
            self._ser = None

    def _checksum(self, payload: bytes) -> int:
        total = sum(payload) & 0xFFFF
        return (0xFFFF - total + 1) & 0xFFFF

    def send(self, cmd: int, param1: int = 0, param2: int = 1) -> None:
        """Send command to DFPlayer with error handling.

        Constructs a 10-byte packet:
        [0x7E, 0xFF, 0x06, cmd, 0x00, param1, param2, checksum_hi, checksum_lo, 0xEF]

        Args:
            cmd: Command byte (0x00-0xFF)
            param1: High-order payload byte (0-255) when a 16-bit parameter is needed
            param2: Low-order payload byte (0-255) when a 16-bit parameter is needed

        Raises:
            ValueError: If parameters are out of valid byte range
            RuntimeError: If serial port is not initialized or closed
        """
        # Validate parameters
        if not (0 <= cmd <= 0xFF):
            raise ValueError(f"Command must be 0-255, got {cmd}")
        if not (0 <= param1 <= 0xFF):
            raise ValueError(f"Param1 must be 0-255, got {param1}")
        if not (0 <= param2 <= 0xFF):
            raise ValueError(f"Param2 must be 0-255, got {param2}")

        if self._ser is None:
            raise RuntimeError("Serial port not initialized, cannot send command")

        try:
            if not self._ser.is_open:
                raise RuntimeError("Serial port is closed, cannot send command")

            # Construct packet
            pkt = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, param1, param2, 0x00, 0x00, 0xEF])

            # Calculate checksum
            cs = self._checksum(pkt[1:7])
            pkt[7], pkt[8] = (cs >> 8) & 0xFF, cs & 0xFF

            self._ser.write(pkt)
            logger.debug(f"Sent command 0x{cmd:02X} with params ({param1}, {param2})")

        except serial.SerialException as e:
            logger.error(f"Serial write failed: {e}")
            raise
        except OSError as e:
            logger.error(f"OS error during serial write: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending command: {e}")
            raise

    def play_track(self, track_number):
        """Play specific track number.

        Args:
            track_number: Track number (1-3000)
        """
        hi = (track_number >> 8) & 0xFF
        lo = track_number & 0xFF
        self.send(self.CMD_PLAY_TRACK, hi, lo)
        logger.info(f"Playing track {track_number}")

    def play_folder(self, folder, track):
        """Play track from specific folder.

        Args:
            folder: Folder number (1-99)
            track: Track number within folder (1-255)
        """
        self.send(self.CMD_PLAY_FOLDER, folder, track)
        logger.info(f"Playing folder {folder}, track {track}")

    def next_track(self):
        """Skip to next track."""
        self.send(self.CMD_NEXT)
        logger.info("Next track")

    def prev_track(self):
        """Skip to previous track."""
        self.send(self.CMD_PREV)
        logger.info("Previous track")

    def play(self):
        """Resume playback."""
        self.send(self.CMD_PLAY)
        logger.info("Play/Resume")

    def pause(self):
        """Pause playback."""
        self.send(self.CMD_PAUSE)
        logger.info("Pause")

    def stop(self):
        """Stop playback."""
        self.send(self.CMD_STOP)
        logger.info("Stop")

    def set_volume(self, volume):
        """Set volume level.

        Args:
            volume: Volume level (0-30)
        """
        volume = max(0, min(30, int(volume)))
        self.send(self.CMD_VOLUME_SET, 0, volume)
        logger.debug(f"Volume set to {volume}")

    def read_response(self, timeout: float = 0.2) -> Optional[bytes]:
        """Read a DFPlayer response packet (10 bytes) if available."""
        if self._ser is None or not self._ser.is_open:
            return None

        original = self._ser.timeout
        try:
            self._ser.timeout = timeout
            packet = self._ser.read(10)
            if len(packet) != 10 or packet[0] != 0x7E or packet[9] != 0xEF:
                return None
            cs = self._checksum(packet[1:7])
            if packet[7] != ((cs >> 8) & 0xFF) or packet[8] != (cs & 0xFF):
                logger.debug("DFPlayer response checksum mismatch")
                return None
            return packet
        except serial.SerialException as e:
            logger.error(f"Serial read failed: {e}")
            return None
        finally:
            self._ser.timeout = original

    def close(self):
        """Close serial connection."""
        if self._ser and hasattr(self._ser, 'is_open') and self._ser.is_open:
            try:
                self._ser.close()
                logger.info("DFPlayer serial port closed")
            except Exception as e:
                logger.warning(f"Error closing DFPlayer serial port: {e}")

    @property
    def is_connected(self):
        """Check if serial port is connected and open."""
        return self._ser is not None and hasattr(self._ser, 'is_open') and self._ser.is_open

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
