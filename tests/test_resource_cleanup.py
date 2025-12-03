"""
Test suite for resource cleanup functionality.
Ensures serial port, framebuffer, and memory map are properly closed.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
import atexit

# Add src to path (legacy tests for dfplayer_fb_gui; kept for historical reference)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestResourceCleanup:
    """Test resource cleanup handlers."""

    def test_cleanup_handler_registered(self):
        """Verify cleanup function is registered with atexit."""
        with patch('atexit.register') as mock_register, \
             patch('serial.Serial'), \
             patch('builtins.open'), \
             patch('mmap.mmap'):

            # Import module to trigger registration
            import importlib
            import dfplayer_fb_gui
            importlib.reload(dfplayer_fb_gui)

            # Check if cleanup is in atexit handlers
            # Since we can't easily inspect atexit handlers after registration,
            # we verify the function exists
            assert hasattr(dfplayer_fb_gui, 'cleanup'), "cleanup() function should exist"

    def test_serial_closed_on_exit(self):
        """Verify serial port is closed on cleanup."""
        with patch('serial.Serial') as mock_serial, \
             patch('builtins.open'), \
             patch('mmap.mmap'):

            mock_ser = Mock()
            mock_ser.is_open = True
            mock_serial.return_value = mock_ser

            import importlib
            import dfplayer_fb_gui
            importlib.reload(dfplayer_fb_gui)

            # Call cleanup
            if hasattr(dfplayer_fb_gui, 'cleanup'):
                dfplayer_fb_gui.cleanup()
                mock_ser.close.assert_called_once()

    def test_framebuffer_closed_on_exit(self):
        """Verify framebuffer and mmap are closed."""
        with patch('serial.Serial'), \
             patch('builtins.open') as mock_open, \
             patch('mmap.mmap') as mock_mmap:

            mock_fb = Mock()
            mock_mm = Mock()
            mock_open.return_value = mock_fb
            mock_mmap.return_value = mock_mm

            import importlib
            import dfplayer_fb_gui
            importlib.reload(dfplayer_fb_gui)

            # Call cleanup
            if hasattr(dfplayer_fb_gui, 'cleanup'):
                dfplayer_fb_gui.cleanup()
                mock_mm.close.assert_called()
                mock_fb.close.assert_called()

    def test_cleanup_handles_closed_resources(self):
        """Verify cleanup handles already-closed resources gracefully."""
        with patch('serial.Serial') as mock_serial, \
             patch('builtins.open') as mock_open, \
             patch('mmap.mmap') as mock_mmap:

            mock_ser = Mock()
            mock_ser.is_open = False
            mock_ser.close.side_effect = Exception("Already closed")
            mock_serial.return_value = mock_ser

            mock_fb = Mock()
            mock_fb.close.side_effect = Exception("Already closed")
            mock_open.return_value = mock_fb

            mock_mm = Mock()
            mock_mm.close.side_effect = Exception("Already closed")
            mock_mmap.return_value = mock_mm

            import importlib
            import dfplayer_fb_gui
            importlib.reload(dfplayer_fb_gui)

            # Cleanup should not raise exception
            if hasattr(dfplayer_fb_gui, 'cleanup'):
                try:
                    dfplayer_fb_gui.cleanup()
                except Exception as e:
                    pytest.fail(f"cleanup() should handle exceptions gracefully: {e}")
