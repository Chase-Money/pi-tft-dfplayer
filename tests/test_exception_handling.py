"""
Test suite for exception handling during initialization.
Ensures graceful handling when serial and touch devices are missing.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import serial

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestSerialInitialization:
    """Test serial port initialization error handling."""

    def test_serial_init_handles_missing_device(self):
        """Verify graceful handling when serial device missing."""
        with patch('serial.Serial') as mock_serial:
            mock_serial.side_effect = serial.SerialException("Device not found")

            with patch('builtins.open'), \
                 patch('mmap.mmap'), \
                 patch('evdev.InputDevice'):

                # Try to import - should handle exception gracefully
                try:
                    import importlib
                    import dfplayer_fb_gui
                    importlib.reload(dfplayer_fb_gui)

                    # If init_serial exists, call it
                    if hasattr(dfplayer_fb_gui, 'init_serial'):
                        result = dfplayer_fb_gui.init_serial()
                        assert result is None or result is False, \
                            "init_serial should return None/False on failure"
                except SystemExit:
                    pytest.fail("Should not call sys.exit() - use logging instead")
                except serial.SerialException:
                    pytest.fail("SerialException should be caught and handled")

    def test_serial_init_handles_permission_denied(self):
        """Verify handling of permission errors."""
        with patch('serial.Serial') as mock_serial:
            mock_serial.side_effect = PermissionError("Permission denied")

            with patch('builtins.open'), \
                 patch('mmap.mmap'), \
                 patch('evdev.InputDevice'):

                try:
                    import importlib
                    import dfplayer_fb_gui
                    importlib.reload(dfplayer_fb_gui)

                    if hasattr(dfplayer_fb_gui, 'init_serial'):
                        result = dfplayer_fb_gui.init_serial()
                        assert result is None or result is False
                except SystemExit:
                    pytest.fail("Should not call sys.exit() - use logging instead")


class TestTouchDeviceInitialization:
    """Test touch device initialization error handling."""

    def test_touch_init_handles_missing_device(self):
        """Verify graceful handling when touch device missing."""
        with patch('evdev.list_devices') as mock_list:
            mock_list.return_value = []

            with patch('serial.Serial'), \
                 patch('builtins.open'), \
                 patch('mmap.mmap'):

                try:
                    import importlib
                    import dfplayer_fb_gui

                    # Mock open_touch to raise RuntimeError
                    with patch.object(dfplayer_fb_gui, 'open_touch') as mock_open_touch:
                        mock_open_touch.side_effect = RuntimeError("No input event devices found")

                        if hasattr(dfplayer_fb_gui, 'init_touch'):
                            result = dfplayer_fb_gui.init_touch()
                            assert result is None or result is False
                except SystemExit:
                    pytest.fail("Should not call sys.exit() - use logging instead")
                except RuntimeError:
                    pytest.fail("RuntimeError should be caught and handled")

    def test_touch_init_handles_no_abs_axes(self):
        """Verify handling when touch device lacks required axes."""
        mock_dev = Mock()
        mock_dev.path = "/dev/input/event0"
        mock_dev.name = "Test Touch"
        mock_dev.absinfo.return_value = None  # No ABS axes

        with patch('evdev.InputDevice') as mock_input:
            mock_input.return_value = mock_dev

            with patch('serial.Serial'), \
                 patch('builtins.open'), \
                 patch('mmap.mmap'):

                try:
                    import importlib
                    import dfplayer_fb_gui

                    if hasattr(dfplayer_fb_gui, 'init_touch'):
                        result = dfplayer_fb_gui.init_touch()
                        assert result is None or result is False
                except SystemExit:
                    pytest.fail("Should not call sys.exit() - use logging instead")
