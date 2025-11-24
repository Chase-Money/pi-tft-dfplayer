"""
DFPlayer backend for the v2 UI framework.
"""
import time
import serial
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class DFPlayerBackend:
    """Handles all serial communication with the DFPlayer Mini module."""

    def __init__(self, port='/dev/serial0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.serial_lock = threading.Lock()

    def initialize(self) -> bool:
        """Initializes the serial connection."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            logger.info(f"Serial port '{self.port}' initialized successfully.")
            self.reset()
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port '{self.port}': {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during serial initialization: {e}")
            return False

    def _checksum(self, payload: bytearray) -> int:
        """Calculates the checksum for a DFPlayer command."""
        total = sum(payload) & 0xFFFF
        return (0xFFFF - total + 1) & 0xFFFF

    def _send_command(self, cmd: int, p1: int = 0, p2: int = 1):
        """Sends a command to the DFPlayer module."""
        if not self.ser:
            logger.warning("Cannot send command, serial port is not initialized.")
            return

        with self.serial_lock:
            try:
                pkt = bytearray([0x7E, 0xFF, 0x06, cmd, 0x00, p1, p2, 0x00, 0x00, 0xEF])
                cs = self._checksum(pkt[1:7])
                pkt[7], pkt[8] = (cs >> 8) & 0xFF, cs & 0xFF
                self.ser.write(pkt)
            except Exception as e:
                logger.error(f"Error sending command 0x{cmd:02x}: {e}")

    def read_response(self, timeout: float = 0.3) -> Optional[bytes]:
        """Reads a 10-byte response from the DFPlayer."""
        if not self.ser:
            return None

        with self.serial_lock:
            original_timeout = self.ser.timeout
            try:
                self.ser.timeout = timeout
                response = self.ser.read(10)
                if len(response) == 10 and response[0] == 0x7E and response[9] == 0xEF:
                    cs = self._checksum(response[1:7])
                    if response[7] == (cs >> 8) & 0xFF and response[8] == cs & 0xFF:
                        return response
                    else:
                        logger.warning("DFPlayer response checksum mismatch.")
                return None
            except Exception as e:
                logger.warning(f"Error reading DFPlayer response: {e}")
                return None
            finally:
                self.ser.timeout = original_timeout

    def play_track(self, track_number: int) -> bool:
        """Plays a specific track number."""
        logger.info(f"Playing track {track_number}")
        hi = (track_number >> 8) & 0xFF
        lo = track_number & 0xFF
        self._send_command(0x03, hi, lo)
        # We could wait for an ACK here if we build a more robust system
        return True

    def set_volume(self, volume: int):
        """Sets the volume (0-30)."""
        vol = max(0, min(30, int(volume)))
        self._send_command(0x06, 0, vol)

    def pause(self):
        """Pauses the current track."""
        self._send_command(0x0E)

    def resume(self):
        """Resumes the current track."""
        self._send_command(0x0D)

    def stop(self):
        """Stops playback."""
        self._send_command(0x16)

    def next_track(self):
        """Plays the next track."""
        self._send_command(0x01)

    def prev_track(self):
        """Plays the previous track."""
        self._send_command(0x02)

    def reset(self):
        """Resets the DFPlayer module."""
        logger.info("Resetting DFPlayer module...")
        self._send_command(0x0C, 0, 0)
        time.sleep(0.5)  # Wait for the module to restart
        self._send_command(0x09, 0, 0x02) # Select TF card
        time.sleep(0.1)
        logger.info("DFPlayer reset complete.")

    def query_file_count(self) -> Optional[int]:
        """Queries the number of files on the TF card."""
        self._send_command(0x48, 0, 0)
        time.sleep(0.2)
        response = self.read_response()
        if response and response[3] == 0x48:
            return (response[5] << 8) | response[6]
        return None

    def cleanup(self):
        """Closes the serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial port closed.")

    def shutdown(self):
        """Alias for cleanup() for compatibility with main app."""
        self.cleanup()
