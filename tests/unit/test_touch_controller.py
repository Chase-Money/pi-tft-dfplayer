"""
Unit tests for TouchController with mocked hardware.

Tests coordinate transformation, calibration, orientation modes, and gesture detection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass


# Mock evdev classes
@dataclass
class MockAbsInfo:
    """Mock evdev AbsInfo."""
    min: int
    max: int
    fuzz: int = 0
    flat: int = 0


@dataclass
class MockInputEvent:
    """Mock evdev input event."""
    type: int
    code: int
    value: int
    timestamp: float = 0.0


class MockInputDevice:
    """Mock evdev InputDevice."""
    def __init__(self, path="/dev/input/event0"):
        self.path = path
        self.name = "Mock Touch Device"
        self._abs_x = MockAbsInfo(min=0, max=4095)
        self._abs_y = MockAbsInfo(min=0, max=4095)

    def absinfo(self, code):
        """Mock absinfo method."""
        if code == 0:  # ABS_X
            return self._abs_x
        elif code == 1:  # ABS_Y
            return self._abs_y
        return None

    def fileno(self):
        return 123

    def read(self):
        return []

    def close(self):
        pass


@pytest.fixture
def mock_evdev():
    """Mock evdev module."""
    with patch('src.hardware.touch.EVDEV_AVAILABLE', True):
        with patch('src.hardware.touch.InputDevice', MockInputDevice):
            with patch('src.hardware.touch.list_devices', return_value=["/dev/input/event0"]):
                # Mock ecodes
                mock_ecodes = Mock()
                mock_ecodes.ABS_X = 0
                mock_ecodes.ABS_Y = 1
                mock_ecodes.EV_ABS = 3
                mock_ecodes.EV_KEY = 1
                mock_ecodes.BTN_TOUCH = 330
                with patch('src.hardware.touch.ecodes', mock_ecodes):
                    yield


@pytest.fixture
def touch_controller(mock_evdev):
    """Create TouchController instance with mocked hardware."""
    from src.hardware.touch_controller import TouchController
    return TouchController()


class TestTouchControllerInitialization:
    """Test touch controller initialization."""

    def test_init_with_auto_detect(self, mock_evdev):
        """Test initialization with auto-detected device."""
        from src.hardware.touch_controller import TouchController
        tc = TouchController()
        assert tc.available is True
        assert tc.touch is not None

    def test_init_with_specific_device(self, mock_evdev):
        """Test initialization with specific device path."""
        from src.hardware.touch_controller import TouchController
        tc = TouchController(device="/dev/input/touchscreen")
        assert tc.available is True

    def test_init_without_evdev(self):
        """Test initialization when evdev is not available."""
        with patch('src.hardware.touch.EVDEV_AVAILABLE', False):
            from src.hardware.touch_controller import TouchController
            tc = TouchController()
            assert tc.available is False
            assert tc.touch is None


class TestCoordinateTransformation:
    """Test coordinate scaling and transformation."""

    def test_basic_scaling(self, touch_controller):
        """Test basic coordinate scaling without calibration."""
        # Touch device range: 0-4095, screen: 480x320
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Center of touch device should map to center of screen
        sx, sy = touch_controller.touch.scale_xy(2048, 2048)
        assert abs(sx - 240) < 5  # Allow small rounding error
        assert abs(sy - 160) < 5

    def test_scaling_with_calibration(self, touch_controller):
        """Test coordinate scaling with custom calibration."""
        touch_controller.set_calibration(100, 4000, 200, 3800)
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Test calibrated center point
        sx, sy = touch_controller.touch.scale_xy(2050, 2000)
        # Should be approximately center
        assert 200 < sx < 280
        assert 130 < sy < 190

    def test_scaling_edge_cases(self, touch_controller):
        """Test coordinate scaling at edges."""
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Top-left corner
        sx, sy = touch_controller.touch.scale_xy(0, 0)
        assert sx == 0
        assert sy == 0

        # Bottom-right corner
        sx, sy = touch_controller.touch.scale_xy(4095, 4095)
        assert sx == 479
        assert sy == 319


class TestOrientationModes:
    """Test all 8 orientation modes (SWAP_XY × FLIP_X × FLIP_Y)."""

    def test_orientation_normal(self, touch_controller):
        """Test normal orientation (no swap, no flip)."""
        touch_controller.set_orientation(swap_xy=False, flip_x=False, flip_y=False)
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        sx, sy = touch_controller.touch.scale_xy(2048, 2048)
        # Center should remain center
        assert 230 < sx < 250
        assert 150 < sy < 170

    def test_orientation_swap_xy(self, touch_controller):
        """Test orientation with swapped X/Y axes."""
        touch_controller.set_orientation(swap_xy=True, flip_x=False, flip_y=False)
        touch_controller.touch.screen_width = 320
        touch_controller.touch.screen_height = 480

        # X and Y should be swapped
        sx, sy = touch_controller.touch.scale_xy(1000, 3000)
        # After swap, original Y becomes X
        assert sx > sy  # Because original Y (3000) > original X (1000)

    def test_orientation_flip_x(self, touch_controller):
        """Test orientation with flipped X axis."""
        touch_controller.set_orientation(swap_xy=False, flip_x=True, flip_y=False)
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Low X should map to high screen X
        sx1, _ = touch_controller.touch.scale_xy(500, 2048)
        sx2, _ = touch_controller.touch.scale_xy(3500, 2048)
        assert sx1 > sx2  # Flipped!

    def test_orientation_flip_y(self, touch_controller):
        """Test orientation with flipped Y axis."""
        touch_controller.set_orientation(swap_xy=False, flip_x=False, flip_y=True)
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Low Y should map to high screen Y
        _, sy1 = touch_controller.touch.scale_xy(2048, 500)
        _, sy2 = touch_controller.touch.scale_xy(2048, 3500)
        assert sy1 > sy2  # Flipped!

    def test_all_eight_orientations(self, touch_controller):
        """Test all 8 possible orientation combinations."""
        orientations = [
            (False, False, False),  # Normal
            (False, False, True),   # Flip Y
            (False, True, False),   # Flip X
            (False, True, True),    # Flip X+Y
            (True, False, False),   # Swap XY
            (True, False, True),    # Swap XY + Flip Y
            (True, True, False),    # Swap XY + Flip X
            (True, True, True),     # Swap XY + Flip X+Y
        ]

        for swap, flip_x, flip_y in orientations:
            touch_controller.set_orientation(swap_xy=swap, flip_x=flip_x, flip_y=flip_y)
            # Just verify no exceptions are raised
            sx, sy = touch_controller.touch.scale_xy(2048, 2048)
            assert 0 <= sx < 480
            assert 0 <= sy < 320


class TestGestureDetection:
    """Test touch gesture detection (tap, drag, swipe)."""

    def test_gesture_tap_detection(self, touch_controller):
        """Test tap gesture detection."""
        # Simulate quick tap: press and release at same location
        from src.hardware.touch_controller import TouchEvent

        # Set screen dimensions for scaling
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Manually set up tap scenario
        # Raw coordinates that will scale to approximately (100, 50)
        # Formula: raw = (screen * (max - min) / (screen_max - 1)) + min
        # For x=100: raw ≈ 100 * 4095 / 479 ≈ 855
        # For y=50: raw ≈ 50 * 4095 / 319 ≈ 642
        touch_controller.last_x = 855
        touch_controller.last_y = 642
        touch_controller.is_pressed = True
        touch_controller.press_x = 100
        touch_controller.press_y = 50
        touch_controller.press_time = 0.0

        # Simulate release (with very small movement)
        import time
        touch_controller.press_time = time.time() - 0.1  # 100ms ago

        # This would normally be called internally
        result = touch_controller._handle_release()

        assert result is not None
        assert result.type == "tap"
        assert result.x == touch_controller.press_x
        assert result.y == touch_controller.press_y

    def test_gesture_drag_detection(self, touch_controller):
        """Test drag gesture detection."""
        import time

        # Simulate drag: press, move moderate distance, release
        touch_controller.last_x = 2500
        touch_controller.last_y = 2500
        touch_controller.is_pressed = True
        touch_controller.press_x = 100
        touch_controller.press_y = 100
        touch_controller.press_time = time.time() - 0.2  # 200ms ago

        result = touch_controller._handle_release()

        assert result is not None
        # Should be drag (moved but not far enough for swipe)
        assert result.type in ["drag", "swipe"]

    def test_swipe_direction_detection(self, touch_controller):
        """Test swipe direction detection."""
        # Right swipe
        assert touch_controller._get_swipe_direction(100, 10) == "right"

        # Left swipe
        assert touch_controller._get_swipe_direction(-100, 10) == "left"

        # Down swipe
        assert touch_controller._get_swipe_direction(10, 100) == "down"

        # Up swipe
        assert touch_controller._get_swipe_direction(10, -100) == "up"


class TestCalibration:
    """Test touch calibration functionality."""

    def test_set_calibration_values(self, touch_controller):
        """Test setting calibration values."""
        touch_controller.set_calibration(100, 4000, 200, 3900)

        cal = touch_controller.touch.calibration
        assert cal is not None
        assert cal[0] == 100  # min_x
        assert cal[1] == 4000  # max_x
        assert cal[2] == 200  # min_y
        assert cal[3] == 3900  # max_y

    def test_calibration_affects_scaling(self, touch_controller):
        """Test that calibration affects coordinate transformation."""
        touch_controller.touch.screen_width = 480
        touch_controller.touch.screen_height = 320

        # Get coordinates without calibration
        sx1, sy1 = touch_controller.touch.scale_xy(2048, 2048)

        # Apply calibration that shifts the range
        touch_controller.set_calibration(500, 3500, 500, 3500)

        # Get coordinates with calibration
        sx2, sy2 = touch_controller.touch.scale_xy(2048, 2048)

        # Coordinates should differ due to calibration
        # (exact values depend on scaling algorithm)
        assert (sx1, sy1) != (sx2, sy2)


class TestResourceCleanup:
    """Test proper resource cleanup."""

    def test_close_controller(self, touch_controller):
        """Test closing touch controller releases resources."""
        touch_controller.close()
        # Should not raise an exception


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_events_when_unavailable(self):
        """Test getting events when touch is unavailable."""
        with patch('src.hardware.touch.EVDEV_AVAILABLE', False):
            from src.hardware.touch_controller import TouchController
            tc = TouchController()
            events = tc.get_events(timeout=0)
            assert events == []

    def test_scaling_with_zero_range(self, touch_controller):
        """Test scaling when min == max (edge case)."""
        # This shouldn't crash
        touch_controller.set_calibration(2000, 2000, 2000, 2000)
        sx, sy = touch_controller.touch.scale_xy(2000, 2000)
        # Should handle gracefully (might clamp to 0 or max)
        assert 0 <= sx < 480
        assert 0 <= sy < 320
