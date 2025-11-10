"""
Test suite for serial command error handling.
Ensures DFPlayer commands handle failures gracefully.
"""
import pytest
import sys
import os
from unittest.mock import patch, Mock
import serial

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestSerialCommandHandling:
    """Test error handling in serial send() function."""

    def test_send_handles_closed_port(self):
        """Verify send() handles closed serial port."""
        with patch('builtins.open'), \
             patch('mmap.mmap'), \
             patch('evdev.InputDevice'):

            import dfplayer_fb_gui

            # Mock closed serial port
            mock_ser = Mock()
            mock_ser.is_open = False
            dfplayer_fb_gui.ser = mock_ser

            # Should not raise exception
            try:
                dfplayer_fb_gui.send(0x01)
                # Verify write was not called on closed port
                mock_ser.write.assert_not_called()
            except Exception as e:
                pytest.fail(f"send() should handle closed port gracefully: {e}")

    def test_send_handles_serial_exception(self):
        """Verify send() handles write failures."""
        with patch('builtins.open'), \
             patch('mmap.mmap'), \
             patch('evdev.InputDevice'):

            import dfplayer_fb_gui

            # Mock serial port that raises exception on write
            mock_ser = Mock()
            mock_ser.is_open = True
            mock_ser.write.side_effect = serial.SerialException("Write failed")
            dfplayer_fb_gui.ser = mock_ser

            # Should not raise exception
            try:
                dfplayer_fb_gui.send(0x01)
            except serial.SerialException:
                pytest.fail("send() should catch SerialException")

    def test_send_handles_os_error(self):
        """Verify send() handles OS-level errors."""
        with patch('builtins.open'), \
             patch('mmap.mmap'), \
             patch('evdev.InputDevice'):

            import dfplayer_fb_gui

            # Mock serial port that raises OSError
            mock_ser = Mock()
            mock_ser.is_open = True
            mock_ser.write.side_effect = OSError("Device not found")
            dfplayer_fb_gui.ser = mock_ser

            # Should not raise exception
            try:
                dfplayer_fb_gui.send(0x01)
            except OSError:
                pytest.fail("send() should catch OSError")

    def test_send_constructs_valid_packet(self):
        """Verify send() constructs valid DFPlayer packet."""
        with patch('builtins.open'), \
             patch('mmap.mmap'), \
             patch('evdev.InputDevice'):

            import dfplayer_fb_gui

            # Mock working serial port
            mock_ser = Mock()
            mock_ser.is_open = True
            dfplayer_fb_gui.ser = mock_ser

            # Send command
            dfplayer_fb_gui.send(0x03, 0x00, 0x01)

            # Verify write was called
            assert mock_ser.write.called, "send() should call ser.write()"

            # Verify packet structure
            call_args = mock_ser.write.call_args[0][0]
            assert len(call_args) == 10, "DFPlayer packet should be 10 bytes"
            assert call_args[0] == 0x7E, "Packet should start with 0x7E"
            assert call_args[9] == 0xEF, "Packet should end with 0xEF"
            assert call_args[3] == 0x03, "Command byte should be 0x03"

    def test_vol_set_clamps_values(self):
        """Verify vol_set() clamps volume to valid range."""
        with patch('builtins.open'), \
             patch('mmap.mmap'), \
             patch('evdev.InputDevice'):

            import dfplayer_fb_gui

            # Mock serial port
            mock_ser = Mock()
            mock_ser.is_open = True
            dfplayer_fb_gui.ser = mock_ser

            # Test clamping high value
            dfplayer_fb_gui.vol_set(50)
            call_args = mock_ser.write.call_args[0][0]
            assert call_args[6] == 30, "Volume should be clamped to 30"

            # Test clamping low value
            dfplayer_fb_gui.vol_set(-5)
            call_args = mock_ser.write.call_args[0][0]
            assert call_args[6] == 0, "Volume should be clamped to 0"
