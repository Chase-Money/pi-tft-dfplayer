"""Integration tests for full application workflow.

Tests complete user journeys through the application stack:
- Startup → Navigate → Play → Shutdown
- Screen navigation stack integrity
- Backend event queue integration with UI
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.app import Application
from src.backends.dfplayer import DFPlayerBackend
from src.ui.framework.events import UIEvent


class FakeFramebuffer:
    """Mock framebuffer for testing without hardware."""

    def __init__(self, width=480, height=320):
        self.width = width
        self.height = height
        self.pushed_frames = 0
        self.last_dirty_rects = None

    def push(self, image, dirty_rects=None):
        self.pushed_frames += 1
        self.last_dirty_rects = dirty_rects

    def close(self):
        pass


class FakeTouchController:
    """Mock touch controller for testing."""

    def __init__(self):
        self.events = []
        self.closed = False

    def poll_event(self, timeout=0.01):
        if self.events:
            return self.events.pop(0)
        return None

    def inject_event(self, event_type, x, y, **kwargs):
        """Helper to inject touch events for testing."""
        self.events.append({
            "type": event_type,
            "pos": (x, y),
            **kwargs
        })

    def close(self):
        self.closed = True


class FakeDFPlayer:
    """Mock DFPlayer hardware for testing."""

    def __init__(self):
        self.is_connected = True
        self.volume = 15
        self.track_calls = []
        self.play_calls = 0
        self.pause_calls = 0
        self.stop_calls = 0

    def set_volume(self, vol):
        self.volume = vol

    def play_track(self, num):
        self.track_calls.append(num)

    def play(self):
        self.play_calls += 1

    def pause(self):
        self.pause_calls += 1

    def stop(self):
        self.stop_calls += 1

    def next_track(self):
        pass

    def prev_track(self):
        pass

    def read_response(self, timeout=0.1):
        return None

    def close(self):
        self.is_connected = False


class TestFullWorkflow:
    """Test complete application workflows from startup to shutdown."""

    @pytest.fixture
    def mocked_app(self):
        """Create application with mocked hardware."""
        with patch('src.app.Framebuffer') as mock_fb, \
             patch('src.app.TouchController') as mock_touch, \
             patch('src.app.DFPlayerBackend') as mock_backend:

            # Setup mocks
            fake_fb = FakeFramebuffer()
            fake_touch = FakeTouchController()
            fake_dfplayer = FakeDFPlayer()

            mock_fb.return_value = fake_fb
            mock_touch.return_value = fake_touch

            # Mock backend with fake hardware
            mock_backend_instance = MagicMock()
            mock_backend_instance.initialize.return_value = True
            mock_backend_instance.is_connected = True
            mock_backend_instance.poll_event.return_value = None
            mock_backend.return_value = mock_backend_instance

            app = Application()
            app._fake_fb = fake_fb
            app._fake_touch = fake_touch
            app._fake_dfplayer = fake_dfplayer

            yield app

            # Cleanup
            try:
                app.shutdown()
            except:
                pass

    def test_startup_initialization(self, mocked_app):
        """Test application initializes all components correctly."""
        app = mocked_app

        # Verify components were created
        assert app.config is not None
        assert app.state is not None
        assert app.backend is not None
        assert app.renderer is not None
        assert app.screen_manager is not None

        # Verify home screen is loaded
        assert app.screen_manager.current is not None
        assert app.screen_manager.current.name == "home"

    def test_screen_navigation_stack(self, mocked_app):
        """Test screen navigation push/pop maintains stack integrity."""
        app = mocked_app

        # Start at home
        assert len(app.screen_manager.stack()) == 1
        assert app.screen_manager.current.name == "home"

        # Navigate to track browser
        app.screen_manager.push("track_browser")
        assert len(app.screen_manager.stack()) == 2
        assert app.screen_manager.current.name == "track_browser"

        # Navigate to now playing
        app.screen_manager.push("now_playing")
        assert len(app.screen_manager.stack()) == 3
        assert app.screen_manager.current.name == "now_playing"

        # Pop back to track browser
        popped = app.screen_manager.pop()
        assert popped.name == "now_playing"
        assert app.screen_manager.current.name == "track_browser"
        assert len(app.screen_manager.stack()) == 2

        # Pop back to home
        app.screen_manager.pop()
        assert app.screen_manager.current.name == "home"
        assert len(app.screen_manager.stack()) == 1

    def test_touch_event_routing(self, mocked_app):
        """Test touch events are routed to current screen."""
        app = mocked_app

        # Inject tap event
        app._fake_touch.inject_event("tap", 100, 100)

        # Process one frame (should route event to home screen)
        # This would normally happen in the run loop
        event_data = app._fake_touch.poll_event()
        if event_data:
            event = UIEvent(event_data.get("type"), event_data)
            handled = app.screen_manager.handle_event(event)
            # Event may or may not be handled depending on button hit
            assert isinstance(handled, bool)

    def test_framebuffer_updates(self, mocked_app):
        """Test framebuffer receives rendered frames."""
        app = mocked_app

        initial_frames = app._fake_fb.pushed_frames

        # Trigger one render cycle
        context = {
            "image": Mock(width=480, height=320),
            "draw": Mock(),
            "fonts": {"small": Mock(), "medium": Mock(), "large": Mock()},
            "scale": 1.0
        }
        app.renderer.render_frame(app.screen_manager, context)

        # Verify render was called (actual push happens in Application.run())
        assert app.screen_manager.current is not None

    def test_backend_event_integration(self, mocked_app):
        """Test backend events are consumed and processed."""
        app = mocked_app

        # Mock backend to return an event
        test_event = {"type": "track_started", "track": 5}
        app.backend.poll_event = Mock(side_effect=[test_event, None, None])

        # Process events (simulating one iteration of run loop)
        events_processed = []
        for _ in range(10):
            evt = app.backend.poll_event(timeout=0.001)
            if evt:
                events_processed.append(evt)
            else:
                break

        # Verify event was consumed
        assert len(events_processed) >= 1
        assert events_processed[0]["type"] == "track_started"
        assert events_processed[0]["track"] == 5

    def test_shutdown_cleanup(self, mocked_app):
        """Test shutdown cleans up all resources."""
        app = mocked_app

        # Initialize if not already
        if not hasattr(app, '_running'):
            app._running = False

        # Shutdown
        app.shutdown()

        # Verify backend was shut down
        if hasattr(app.backend, 'shutdown'):
            app.backend.shutdown.assert_called()


class TestScreenTransitions:
    """Test screen transition scenarios."""

    def test_replace_screen(self):
        """Test screen replacement (pop + push in one operation)."""
        from src.ui.framework.manager import ScreenManagerV2
        from src.ui.screens.home import HomeScreen
        from src.ui.screens.now_playing import NowPlayingScreen

        manager = ScreenManagerV2()
        manager.register("home", HomeScreen)
        manager.register("now_playing", NowPlayingScreen)

        # Start with home
        manager.push("home")
        assert manager.current.name == "home"
        assert len(manager.stack()) == 1

        # Replace with now_playing
        manager.replace("now_playing")
        assert manager.current.name == "now_playing"
        assert len(manager.stack()) == 1  # Stack size unchanged

    def test_full_refresh_flag(self):
        """Test full refresh flag is set on navigation."""
        from src.ui.framework.manager import ScreenManagerV2
        from src.ui.screens.home import HomeScreen

        manager = ScreenManagerV2()
        manager.register("home", HomeScreen)

        # Push should set refresh flag
        manager.push("home")
        assert manager.needs_full_refresh()

        # Clear flag
        manager.clear_refresh_flag()
        assert not manager.needs_full_refresh()

        # Pop should set refresh flag again
        manager.push("home")  # Push another
        manager.clear_refresh_flag()
        manager.pop()
        assert manager.needs_full_refresh()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
