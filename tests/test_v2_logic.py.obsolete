"""
Tests for the v2 refactored application logic.
"""

import pytest
from unittest.mock import Mock, patch

# Add src to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dfplayer_fb_gui_v2 import App
from core.app_state import AppState
from ui.components import Button

@pytest.fixture
def mock_hardware():
    """Fixture to mock all hardware components."""
    with patch('dfplayer_fb_gui_v2.Framebuffer') as mock_fb_class, \
         patch('dfplayer_fb_gui_v2.TouchController') as mock_touch_class, \
         patch('dfplayer_fb_gui_v2.DFPlayer') as mock_dfplayer_class, \
         patch('dfplayer_fb_gui_v2.get_config') as mock_get_config:
        
        mock_fb_class.return_value.width = 480
        mock_fb_class.return_value.height = 320
        
        yield {
            "framebuffer_class": mock_fb_class,
            "touch_controller_class": mock_touch_class,
            "dfplayer_class": mock_dfplayer_class,
            "get_config": mock_get_config,
            "framebuffer": mock_fb_class.return_value,
            "touch_controller": mock_touch_class.return_value,
            "dfplayer": mock_dfplayer_class.return_value,
        }

def test_app_initialization(mock_hardware):
    """Test that the App class initializes correctly."""
    app = App()
    assert isinstance(app.state, AppState)
    assert app.screen is not None
    assert "play" in app.components
    mock_hardware["framebuffer_class"].assert_called_once()
    mock_hardware["touch_controller_class"].assert_called_once()
    mock_hardware["dfplayer_class"].assert_called_once()

def test_play_button_action(mock_hardware):
    """Test the play/pause button logic."""
    app = App()
    
    # Test play
    app.state.is_playing = False
    app.handle_play_button()
    assert app.state.is_playing is True
    mock_hardware["dfplayer"].play.assert_called_once()

    # Test pause
    app.handle_play_button()
    assert app.state.is_playing is False
    mock_hardware["dfplayer"].pause.assert_called_once()

def test_stop_button_action(mock_hardware):
    """Test the stop button logic."""
    app = App()
    app.handle_stop_button()
    assert app.state.is_playing is False
    mock_hardware["dfplayer"].stop.assert_called_once()

def test_track_scrolling(mock_hardware):
    """Test the track list scrolling logic."""
    app = App()
    app.state.tracks = [{"number": i, "title": f"Track {i}"} for i in range(1, 21)]
    
    # Scroll down
    app.state.track_scroll_position = 0
    app.handle_scroll_down()
    assert app.state.track_scroll_position == 1

    # Scroll up
    app.handle_scroll_up()
    assert app.state.track_scroll_position == 0

    # Scroll to end
    app.state.track_scroll_position = 18
    app.handle_scroll_down()
    assert app.state.track_scroll_position == 19
    
    # Can't scroll past end
    app.handle_scroll_down()
    assert app.state.track_scroll_position == 19

def test_cfg_button_action(mock_hardware):
    """Test the CFG button logic."""
    app = App()
    initial_orientation = app.state.orientation_index
    
    app.handle_cfg_button()
    
    assert app.state.orientation_index == (initial_orientation + 1) % 8
    mock_hardware["get_config"].return_value.set_touch_orientation.assert_called_with(app.state.orientation_index)
    mock_hardware["get_config"].return_value.save.assert_called_once()

