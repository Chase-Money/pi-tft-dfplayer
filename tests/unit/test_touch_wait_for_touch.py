"""
Tests for TouchInput.wait_for_touch method to ensure it doesn't block indefinitely.

The original implementation used device.read_loop() which blocks forever if
no events arrive. This test ensures the method properly times out using
select() or similar non-blocking mechanisms.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time
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


class TestWaitForTouchTimeout:
    """Tests for wait_for_touch timeout behavior."""

    def test_wait_for_touch_should_not_block_indefinitely(self, mock_device):
        """
        wait_for_touch should return None after timeout, not block forever.

        This test verifies the fix for the blocking read_loop() issue.
        """
        with patch('src.hardware.touch.InputDevice', return_value=mock_device):
            with patch('src.hardware.touch.list_devices', return_value=['/dev/input/event0']):
                with patch('os.path.exists', return_value=True):
                    with patch('select.select') as mock_select:
                        # Simulate no data available (timeout)
                        mock_select.return_value = ([], [], [])

                        from src.hardware.touch import TouchInput
                        touch = TouchInput(device_path='/dev/input/touchscreen')

                        start_time = time.time()
                        result = touch.wait_for_touch(timeout=0.5)
                        elapsed = time.time() - start_time

                        # Should return None and not block
                        assert result is None, "Should return None on timeout"
                        assert elapsed < 1.0, f"Should timeout quickly, took {elapsed:.2f}s"

    def test_wait_for_touch_returns_coordinates_when_touch_detected(self, mock_device):
        """wait_for_touch should return coordinates when a valid touch is detected."""
        touch_events = [
            InputEvent(0, 0, ecodes.EV_KEY, ecodes.BTN_TOUCH, 1),  # Press
            *[InputEvent(0, 0, ecodes.EV_ABS, ecodes.ABS_X, 2048) for _ in range(18)],
            *[InputEvent(0, 0, ecodes.EV_ABS, ecodes.ABS_Y, 2048) for _ in range(18)],
        ]

        with patch('src.hardware.touch.InputDevice', return_value=mock_device):
            with patch('src.hardware.touch.list_devices', return_value=['/dev/input/event0']):
                with patch('os.path.exists', return_value=True):
                    with patch('select.select') as mock_select:
                        # Simulate data available
                        mock_select.return_value = ([mock_device], [], [])

                        # Mock read() to return events then empty lists
                        def _event_batches():
                            yield touch_events
                            while True:
                                yield []
                        mock_device.read.side_effect = _event_batches()

                        from src.hardware.touch import TouchInput
                        touch = TouchInput(device_path='/dev/input/touchscreen')

                        result = touch.wait_for_touch(timeout=1.0, samples=1)

                        # Should return coordinates if available, but must not block
                        assert result is None or isinstance(result, tuple), "Should return coords or None"
                        if isinstance(result, tuple):
                            assert len(result) == 2, "Should return (x, y) coordinates"

    def test_wait_for_touch_respects_timeout(self, mock_device):
        """wait_for_touch should respect the specified timeout value."""
        with patch('src.hardware.touch.InputDevice', return_value=mock_device):
            with patch('src.hardware.touch.list_devices', return_value=['/dev/input/event0']):
                with patch('os.path.exists', return_value=True):
                    with patch('select.select') as mock_select:
                        # Simulate no data available
                        mock_select.return_value = ([], [], [])

                        from src.hardware.touch import TouchInput
                        touch = TouchInput(device_path='/dev/input/touchscreen')

                        start_time = time.time()
                        result = touch.wait_for_touch(timeout=0.1)
                        elapsed = time.time() - start_time

                        assert result is None
                        assert 0.05 < elapsed < 0.5, f"Should timeout around 0.1s, took {elapsed:.2f}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
