"""
RobustSerial: wrapper around serial.Serial with auto-reconnect on errors.
Intended for DFPlayer UART resilience.
"""

import logging
import time
from typing import Optional

import serial

logger = logging.getLogger(__name__)


class RobustSerial:
    def __init__(self, device="/dev/serial0", baudrate=9600, timeout=0.1, reconnect_delay=2.0):
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.ser: Optional[serial.Serial] = None
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.device, self.baudrate, timeout=self.timeout)
            logger.info(f"RobustSerial connected to {self.device}")
        except Exception as e:
            logger.error(f"RobustSerial failed to open {self.device}: {e}")
            self.ser = None

    def write(self, data: bytes) -> bool:
        if not self.ser or not getattr(self.ser, "is_open", False):
            self._connect()
            if not self.ser:
                return False
        try:
            self.ser.write(data)
            return True
        except (serial.SerialException, OSError) as e:
            logger.warning(f"Serial write error: {e}; retrying after reconnect")
            self._reconnect()
            try:
                self.ser.write(data)
                return True
            except Exception as e2:
                logger.error(f"Serial write failed after reconnect: {e2}")
                return False
        except Exception as e:
            logger.error(f"Unexpected serial write error: {e}")
            return False

    def read(self, size=1) -> Optional[bytes]:
        if not self.ser or not getattr(self.ser, "is_open", False):
            self._connect()
            if not self.ser:
                return None
        try:
            return self.ser.read(size)
        except (serial.SerialException, OSError) as e:
            logger.warning(f"Serial read error: {e}; retrying after reconnect")
            self._reconnect()
            try:
                return self.ser.read(size)
            except Exception as e2:
                logger.error(f"Serial read failed after reconnect: {e2}")
                return None
        except Exception as e:
            logger.error(f"Unexpected serial read error: {e}")
            return None

    def _reconnect(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        time.sleep(self.reconnect_delay)
        self._connect()

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            logger.error("Error closing RobustSerial", exc_info=True)
        self.ser = None
