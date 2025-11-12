"""DFPlayer Mini UART interface module.

Handles serial communication with the DFPlayer Mini MP3 module over UART.
Implements the DFPlayer command protocol with checksums and error handling.
"""

import logging
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

    def __init__(self, port='/dev/serial0', baudrate=9600, timeout=0.1):
        """Initialize DFPlayer interface.

        Args:
            port: Serial port path
            baudrate: Communication baudrate
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser = None
        self._connect()

    def _connect(self):
        """Establish serial connection with error handling."""
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"DFPlayer connected on {self.port}")
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            logger.error("DFPlayer commands will not work. Check connection.")
            self._ser = None
        except PermissionError as e:
            logger.error(f"Permission denied accessing {self.port}: {e}")
            logger.error("Try: sudo usermod -a -G dialout $USER")
            self._ser = None
        except Exception as e:
            logger.error(f"Unexpected error initializing serial: {e}")
            self._ser = None

    def send(self, cmd, param1=0, param2=1):
        """Send command to DFPlayer with error handling.

        Constructs a 10-byte packet:
        [0x7E, 0xFF, 0x06, cmd, 0x00, param1, param2, checksum_hi, checksum_lo, 0xEF]

        Args:
            cmd: Command byte
            param1: First parameter byte (high byte for 16-bit values)
            param2: Second parameter byte (low byte for 16-bit values)
        """
        if self._ser is None:
            logger.warning("Serial port not initialized, cannot send command")
            return

        try:
            if not self._ser.is_open:
                logger.warning("Serial port is closed, cannot send command")
                return

            # Construct packet
            pkt = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, param1, param2, 0x00, 0x00, 0xEF])

            # Calculate checksum
            cs = (-sum(pkt[1:7])) & 0xFFFF
            pkt[7], pkt[8] = (cs >> 8) & 0xFF, cs & 0xFF

            self._ser.write(pkt)
            logger.debug(f"Sent command 0x{cmd:02X} with params ({param1}, {param2})")

        except serial.SerialException as e:
            logger.error(f"Serial write failed: {e}")
        except OSError as e:
            logger.error(f"OS error during serial write: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending command: {e}")

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
