"""
Mock hardware components for testing without physical devices.

Provides in-memory implementations of framebuffer, touch controller,
and DFPlayer serial that can run on desktop systems.
"""

import io
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass


class MockFramebuffer:
    """
    Mock framebuffer with in-memory RGB565 buffer.

    Allows testing rendering without actual hardware.
    """

    def __init__(self, width: int = 480, height: int = 320):
        """
        Initialize mock framebuffer.

        Args:
            width: Framebuffer width in pixels
            height: Framebuffer height in pixels
        """
        self.width = width
        self.height = height
        self.device = "/dev/fb0"  # Fake device path
        self.buffer_size = width * height * 2  # RGB565 = 2 bytes per pixel
        self.buffer = bytearray(self.buffer_size)
        self.write_count = 0

    def push(self, img):
        """
        Simulate pushing an image to framebuffer.

        Args:
            img: PIL Image to push
        """
        # Just count writes for testing
        self.write_count += 1

        # Optionally store the image for verification
        if hasattr(self, '_last_image'):
            self._last_image = img
        else:
            self._last_image = img

    def close(self):
        """Close the mock framebuffer."""
        self.buffer = None

    def get_last_image(self):
        """Get the last image pushed to framebuffer."""
        return getattr(self, '_last_image', None)

    def clear(self):
        """Clear the framebuffer buffer."""
        self.buffer = bytearray(self.buffer_size)
        self.write_count = 0


@dataclass
class MockTouchEvent:
    """Mock touch event."""
    type: str  # 'press', 'release', 'move'
    x: int
    y: int
    timestamp: float


class MockTouchDevice:
    """
    Mock touch device with programmable event sequence.

    Allows testing touch event processing without physical hardware.
    """

    def __init__(self, width: int = 480, height: int = 320):
        """
        Initialize mock touch device.

        Args:
            width: Touch device width
            height: Touch device height
        """
        self.width = width
        self.height = height
        self.min_x = 0
        self.max_x = 4095
        self.min_y = 0
        self.max_y = 4095

        # Event queue
        self._events: List[MockTouchEvent] = []
        self._event_index = 0

        # Calibration
        self.calibration: Optional[Tuple[int, int, int, int]] = None
        self.orientation = {"SWAP_XY": False, "FLIP_X": False, "FLIP_Y": False}

    def queue_tap(self, x: int, y: int):
        """
        Queue a tap event.

        Args:
            x: Touch X coordinate (screen coordinates)
            y: Touch Y coordinate (screen coordinates)
        """
        raw_x, raw_y = self._screen_to_raw(x, y)
        ts = time.time()

        self._events.append(MockTouchEvent('press', raw_x, raw_y, ts))
        self._events.append(MockTouchEvent('release', raw_x, raw_y, ts + 0.1))

    def queue_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 10):
        """
        Queue a drag event.

        Args:
            start_x: Start X coordinate
            start_y: Start Y coordinate
            end_x: End X coordinate
            end_y: End Y coordinate
            steps: Number of intermediate points
        """
        raw_start_x, raw_start_y = self._screen_to_raw(start_x, start_y)
        raw_end_x, raw_end_y = self._screen_to_raw(end_x, end_y)

        ts = time.time()
        self._events.append(MockTouchEvent('press', raw_start_x, raw_start_y, ts))

        for i in range(1, steps + 1):
            t = i / steps
            x = int(raw_start_x + (raw_end_x - raw_start_x) * t)
            y = int(raw_start_y + (raw_end_y - raw_start_y) * t)
            self._events.append(MockTouchEvent('move', x, y, ts + 0.01 * i))

        self._events.append(MockTouchEvent('release', raw_end_x, raw_end_y, ts + 0.01 * (steps + 1)))

    def get_next_event(self) -> Optional[MockTouchEvent]:
        """
        Get next event from queue.

        Returns:
            Next MockTouchEvent or None if queue empty
        """
        if self._event_index < len(self._events):
            event = self._events[self._event_index]
            self._event_index += 1
            return event
        return None

    def reset_queue(self):
        """Reset event queue."""
        self._events = []
        self._event_index = 0

    def _screen_to_raw(self, sx: int, sy: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to raw touch coordinates.

        Args:
            sx: Screen X
            sy: Screen Y

        Returns:
            (raw_x, raw_y) tuple
        """
        # Inverse of scaling transformation
        raw_x = int(sx * (self.max_x - self.min_x) / (self.width - 1) + self.min_x)
        raw_y = int(sy * (self.max_y - self.min_y) / (self.height - 1) + self.min_y)
        return raw_x, raw_y


class MockDFPlayerSerial:
    """
    Mock DFPlayer serial port with command logging.

    Simulates DFPlayer serial communication for testing.
    """

    def __init__(self, port: str = '/dev/serial0', baudrate: int = 9600):
        """
        Initialize mock serial port.

        Args:
            port: Port name (not used in mock)
            baudrate: Baudrate (not used in mock)
        """
        self.port = port
        self.baudrate = baudrate
        self.is_open = True

        # Command log
        self.commands: List[bytes] = []

        # Response queue
        self._responses: List[bytes] = []
        self._response_index = 0

        # State tracking
        self.current_track = 1
        self.current_volume = 15
        self.is_playing = False

    def write(self, data: bytes):
        """
        Write command to serial port (mock).

        Args:
            data: Command bytes
        """
        if not self.is_open:
            raise IOError("Port is closed")

        self.commands.append(data)

        # Parse command and update state
        if len(data) >= 10:
            cmd = data[3]

            if cmd == 0x0F:  # Play folder/track
                self.current_track = (data[5] << 8) | data[6]
                self.is_playing = True
            elif cmd == 0x06:  # Set volume
                self.current_volume = data[6]
            elif cmd == 0x16:  # Stop
                self.is_playing = False
            elif cmd == 0x0D:  # Play
                self.is_playing = True
            elif cmd == 0x0E:  # Pause
                self.is_playing = False
            elif cmd == 0x01:  # Next
                self.current_track += 1
                self.is_playing = True
            elif cmd == 0x02:  # Previous
                self.current_track = max(1, self.current_track - 1)
                self.is_playing = True

    def read(self, size: int = 1) -> bytes:
        """
        Read from serial port (mock).

        Args:
            size: Number of bytes to read

        Returns:
            Response bytes
        """
        if not self.is_open:
            raise IOError("Port is closed")

        if self._response_index < len(self._responses):
            response = self._responses[self._response_index]
            self._response_index += 1
            return response

        return b''  # No response available

    def queue_response(self, response: bytes):
        """
        Queue a response to be returned by read().

        Args:
            response: Response bytes
        """
        self._responses.append(response)

    def close(self):
        """Close the mock serial port."""
        self.is_open = False

    def get_last_command(self) -> Optional[bytes]:
        """
        Get the last command sent.

        Returns:
            Last command bytes or None
        """
        return self.commands[-1] if self.commands else None

    def get_command_count(self) -> int:
        """
        Get number of commands sent.

        Returns:
            Command count
        """
        return len(self.commands)

    def clear_commands(self):
        """Clear command history."""
        self.commands = []

    def get_state(self) -> dict:
        """
        Get current DFPlayer state.

        Returns:
            State dictionary
        """
        return {
            'track': self.current_track,
            'volume': self.current_volume,
            'playing': self.is_playing
        }


def create_mock_hardware_suite() -> dict:
    """
    Create a complete suite of mock hardware for testing.

    Returns:
        Dictionary with mock hardware instances:
        - framebuffer: MockFramebuffer
        - touch: MockTouchDevice
        - serial: MockDFPlayerSerial
    """
    return {
        'framebuffer': MockFramebuffer(width=480, height=320),
        'touch': MockTouchDevice(width=480, height=320),
        'serial': MockDFPlayerSerial(port='/dev/serial0')
    }


# Pytest fixtures for convenience
try:
    import pytest

    @pytest.fixture
    def mock_framebuffer():
        """Pytest fixture for mock framebuffer."""
        return MockFramebuffer()

    @pytest.fixture
    def mock_touch_device():
        """Pytest fixture for mock touch device."""
        return MockTouchDevice()

    @pytest.fixture
    def mock_dfplayer_serial():
        """Pytest fixture for mock DFPlayer serial."""
        return MockDFPlayerSerial()

    @pytest.fixture
    def mock_hardware_suite():
        """Pytest fixture for complete hardware suite."""
        return create_mock_hardware_suite()

except ImportError:
    # pytest not available, skip fixtures
    pass
