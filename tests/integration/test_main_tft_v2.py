"""Integration tests for main_tft_v2.py application."""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from main_tft_v2 import DFPlayerTFTApp
from ui.framework.events import UIEvent


class TestDFPlayerTFTAppInitialization(unittest.TestCase):
    """Test application initialization and configuration."""

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    def test_app_initialization_success(self, mock_backend, mock_fb, mock_touch):
        """Test successful initialization of all components."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        result = app.initialize()

        # Assertions
        self.assertTrue(result, "App initialization should succeed")
        self.assertIsNotNone(app.framebuffer, "Framebuffer should be initialized")
        self.assertIsNotNone(app.touch, "Touch controller should be initialized")
        self.assertIsNotNone(app.backend, "Backend should be initialized")
        self.assertIsNotNone(app.state, "State should be initialized")
        self.assertIsNotNone(app.screen_manager, "Screen manager should be initialized")
        self.assertIsNotNone(app.renderer, "Renderer should be initialized")

        # Cleanup
        app.cleanup()

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    def test_app_initialization_without_touch(self, mock_backend, mock_fb, mock_touch):
        """Test app continues when touch initialization fails."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        # Touch initialization fails
        mock_touch.side_effect = Exception("Touch device not found")

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        result = app.initialize()

        # Assertions
        self.assertTrue(result, "App should continue without touch")
        self.assertIsNone(app.touch, "Touch should be None when initialization fails")
        self.assertIsNotNone(app.framebuffer, "Framebuffer should still be initialized")

        # Cleanup
        app.cleanup()

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    def test_app_initialization_fails_without_framebuffer(self, mock_fb, mock_touch):
        """Test app fails when framebuffer initialization fails."""
        # Framebuffer initialization fails
        mock_fb.side_effect = Exception("Framebuffer not found")

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        result = app.initialize()

        # Assertions
        self.assertFalse(result, "App should fail without framebuffer")
        self.assertIsNone(app.framebuffer, "Framebuffer should be None")

        # Cleanup
        app.cleanup()


class TestTouchEventConversion(unittest.TestCase):
    """Test touch event to UI event conversion."""

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    def test_tap_event_conversion(self, mock_backend, mock_fb, mock_touch):
        """Test tap event is converted correctly to UIEvent."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        app.initialize()

        # Create mock touch event
        touch_event = Mock()
        touch_event.type = 'tap'
        touch_event.x = 100
        touch_event.y = 200

        # Convert to UI event
        ui_event = app._touch_to_ui_event(touch_event)

        # Assertions
        self.assertIsNotNone(ui_event, "UI event should be created")
        self.assertEqual(ui_event.type, "tap", "Event type should be 'tap'")
        self.assertIn("pos", ui_event.payload, "Payload should contain 'pos'")
        self.assertEqual(ui_event.payload["pos"], (100, 200), "Position should match")

        # Test that get_point() works correctly
        point = ui_event.get_point()
        self.assertEqual(point, (100, 200), "get_point() should return correct coordinates")

        # Cleanup
        app.cleanup()

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    def test_drag_event_conversion(self, mock_backend, mock_fb, mock_touch):
        """Test drag event is converted correctly to UIEvent."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        app.initialize()

        # Create mock drag event
        touch_event = Mock()
        touch_event.type = 'drag'
        touch_event.x = 150
        touch_event.y = 250
        touch_event.dx = 10
        touch_event.dy = -5

        # Convert to UI event
        ui_event = app._touch_to_ui_event(touch_event)

        # Assertions
        self.assertIsNotNone(ui_event, "UI event should be created")
        self.assertEqual(ui_event.type, "drag", "Event type should be 'drag'")
        self.assertIn("pos", ui_event.payload, "Payload should contain 'pos'")
        self.assertEqual(ui_event.payload["pos"], (150, 250), "Position should match")
        self.assertEqual(ui_event.payload["dx"], 10, "dx should match")
        self.assertEqual(ui_event.payload["dy"], -5, "dy should match")

        # Cleanup
        app.cleanup()


class TestTrackLoading(unittest.TestCase):
    """Test track catalog loading functionality."""

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    @patch('os.path.exists')
    def test_track_loading_from_catalog_file(self, mock_exists, mock_backend, mock_fb, mock_touch):
        """Test loading tracks from catalog file."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Mock file exists for catalog
        mock_exists.return_value = True

        # Create app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")

        # Mock catalog file content
        catalog_content = "1|Track One\n2|Track Two\n3|Track Three\n"
        with patch('builtins.open', unittest.mock.mock_open(read_data=catalog_content)):
            tracks = app._load_tracks()

        # Assertions
        self.assertEqual(len(tracks), 3, "Should load 3 tracks")
        self.assertEqual(tracks[0]["number"], 1)
        self.assertEqual(tracks[0]["title"], "Track One")
        self.assertEqual(tracks[2]["number"], 3)
        self.assertEqual(tracks[2]["title"], "Track Three")

        # Cleanup
        app.cleanup()

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    @patch('os.path.exists')
    def test_track_loading_fallback_to_dfplayer_query(self, mock_exists, mock_backend, mock_fb, mock_touch):
        """Test fallback to DFPlayer query when no catalog file exists."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend_instance.query_file_count.return_value = 15
        mock_backend.return_value = mock_backend_instance

        # No catalog file exists
        mock_exists.return_value = False

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        app.initialize()

        # Check tracks were generated from DFPlayer query
        self.assertEqual(len(app.state.tracks), 15, "Should have 15 tracks from DFPlayer query")

        # Cleanup
        app.cleanup()


class TestResourceCleanup(unittest.TestCase):
    """Test proper resource cleanup."""

    @patch('main_tft_v2.TouchController')
    @patch('main_tft_v2.Framebuffer')
    @patch('main_tft_v2.DFPlayerBackend')
    def test_cleanup_order(self, mock_backend, mock_fb, mock_touch):
        """Test resources are cleaned up in correct order."""
        # Setup mocks
        mock_fb_instance = Mock()
        mock_fb_instance.width = 480
        mock_fb_instance.height = 320
        mock_fb.return_value = mock_fb_instance

        mock_touch_instance = Mock()
        mock_touch.return_value = mock_touch_instance

        mock_backend_instance = Mock()
        mock_backend_instance.initialize.return_value = True
        mock_backend.return_value = mock_backend_instance

        # Create and initialize app
        app = DFPlayerTFTApp(fb_device="/dev/fb0")
        app.initialize()

        # Cleanup
        app.cleanup()

        # Verify cleanup methods were called
        mock_backend_instance.shutdown.assert_called_once()
        mock_touch_instance.close.assert_called_once()
        mock_fb_instance.close.assert_called_once()

        # Verify resources are None after cleanup
        self.assertIsNone(app.backend)
        self.assertIsNone(app.touch)
        self.assertIsNone(app.framebuffer)
        self.assertIsNone(app.renderer)


if __name__ == '__main__':
    unittest.main()
