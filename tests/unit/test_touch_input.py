"""
Tests for the TouchInput class from src/hardware/touch.py.

This test suite verifies the basic touch input functionality including
event reading, coordinate scaling, and device detection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from evdev import InputEvent, ecodes


@pytest.fixture
def mock_device():
    """Create a mock evdev InputDevice."""
    device = Mock()
    device.fileno.return_value = 10
    device.name = "ADS7846 Touchscreen"

    # Mock absolute axis info
    abs_info_x = Mock()
    abs_info_x.min = 0
    abs_info_x.max = 4095

    abs_info_y = Mock()
    abs_info_y.min = 0
    abs_info_y.max = 4095

    device.absinfo.side_effect = lambda code: {
        ecodes.ABS_X: abs_info_x,
        ecodes.ABS_Y: abs_info_y
    }.get(code)

    return device


@pytest.fixture
def touch_input(mock_device):
    """Create a TouchInput instance with a mocked device."""
    with patch('src.hardware.touch.InputDevice', return_value=mock_device):
        with patch('src.hardware.touch.list_devices', return_value=['/dev/input/event0']):
            with patch('os.path.exists', return_value=True):
                from src.hardware.touch import TouchInput
                touch = TouchInput(device_path='/dev/input/touchscreen')
                return touch


class TestTouchInputReadEvent:
    """Tests for the read_event method - the critical bug fix."""

    def test_read_event_returns_single_event_not_list(self, touch_input, mock_device):
        """
        CRITICAL BUG: read_event() should return a single InputEvent object,
        not a list. Callers expect to access .type and .code attributes directly.

        Before fix: device.read() returns a list, causing AttributeError
        After fix: Should return a single event object or None
        """
        # Simulate evdev returning a list of events (what device.read() actually does)
        mock_event = InputEvent(0, 0, ecodes.EV_ABS, ecodes.ABS_X, 2048)
        mock_device.read.return_value = [mock_event]

        # Call read_event
        result = touch_input.read_event()

        # ASSERTION: Result should be a single event object, not a list
        assert result is not None, "read_event should return an event when available"
        assert not isinstance(result, list), "read_event must NOT return a list"
        assert hasattr(result, 'type'), "Result should have .type attribute"
        assert hasattr(result, 'code'), "Result should have .code attribute"
        assert result.type == ecodes.EV_ABS
        assert result.code == ecodes.ABS_X

    def test_read_event_returns_none_when_no_events(self, touch_input, mock_device):
        """read_event should return None when no events are available."""
        mock_device.read.return_value = []

        result = touch_input.read_event()

        assert result is None, "read_event should return None when no events available"

    def test_read_event_returns_none_on_blocking_io_error(self, touch_input, mock_device):
        """read_event should return None on BlockingIOError (non-blocking read)."""
        mock_device.read.side_effect = BlockingIOError()

        result = touch_input.read_event()

        assert result is None, "read_event should return None on BlockingIOError"

    def test_read_event_returns_none_when_device_is_none(self):
        """read_event should return None when device is not initialized."""
        with patch('src.hardware.touch.list_devices', return_value=[]):
            from src.hardware.touch import TouchInput

            # This should raise RuntimeError, but let's mock it
            with patch.object(TouchInput, '_find_device', return_value=None):
                touch = TouchInput.__new__(TouchInput)
                touch.device = None

                result = touch.read_event()

                assert result is None, "read_event should return None when device is None"


class TestTouchInputScaleXY:
    """Tests for coordinate scaling and transformation."""

    def test_scale_xy_basic(self, touch_input):
        """Test basic coordinate scaling without transformations."""
        # Center of touch input (2048, 2048) should map to center of screen (240, 160)
        sx, sy = touch_input.scale_xy(2048, 2048)

        # With 480x320 screen and 0-4095 input range
        assert 230 <= sx <= 250, f"Expected sx near 240, got {sx}"
        assert 150 <= sy <= 170, f"Expected sy near 160, got {sy}"

    def test_scale_xy_with_flip_x(self, touch_input):
        """Test coordinate scaling with X-axis flip."""
        touch_input.orientation = {'SWAP_XY': False, 'FLIP_X': True, 'FLIP_Y': False}

        # Left edge (x=0) should map to right edge after flip
        sx, sy = touch_input.scale_xy(0, 2048)

        assert sx > 400, f"Flipped X should be near right edge, got {sx}"

    def test_scale_xy_with_swap_xy(self, touch_input):
        """Test coordinate scaling with XY swap (90° rotation)."""
        touch_input.orientation = {'SWAP_XY': True, 'FLIP_X': False, 'FLIP_Y': False}

        # When swapped, x and y should be exchanged
        sx1, sy1 = touch_input.scale_xy(1000, 3000)
        sx2, sy2 = touch_input.scale_xy(3000, 1000)

        # After swap, sx1 should be similar to sy2 and sy1 should be similar to sx2
        assert abs(sx1 - sy2) < 10, "SWAP_XY should exchange coordinates"
        assert abs(sy1 - sx2) < 10, "SWAP_XY should exchange coordinates"


class TestTouchInputDeviceDetection:
    """Tests for touch device detection and initialization."""

    def test_fileno_returns_device_fileno(self, touch_input, mock_device):
        """fileno() should return the device's file descriptor."""
        assert touch_input.fileno() == 10

    def test_fileno_returns_negative_when_no_device(self):
        """fileno() should return -1 when device is None."""
        from src.hardware.touch import TouchInput

        with patch.object(TouchInput, '_find_device', return_value=None):
            touch = TouchInput.__new__(TouchInput)
            touch.device = None

            assert touch.fileno() == -1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
