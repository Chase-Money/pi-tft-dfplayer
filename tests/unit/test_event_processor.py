"""Unit tests for the EventProcessor class."""

import pytest
from unittest.mock import Mock

from core.event_processor import EventProcessor
from ui.framework.events import UIEvent


class TestEventProcessor:
    """Test cases for EventProcessor."""

    def test_touch_to_ui_event_tap(self):
        """Test conversion of tap touch event to UI event."""
        processor = EventProcessor()

        # Mock touch event
        touch_event = Mock()
        touch_event.type = "tap"
        touch_event.x = 100
        touch_event.y = 200
        touch_event.raw_x = 1000
        touch_event.raw_y = 2000

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "tap"
        assert ui_event.payload["pos"] == (100, 200)
        assert ui_event.payload["raw"] == (1000, 2000)

    def test_touch_to_ui_event_drag(self):
        """Test conversion of drag touch event to UI event."""
        processor = EventProcessor()

        touch_event = Mock()
        touch_event.type = "drag"
        touch_event.x = 150
        touch_event.y = 250
        touch_event.dx = 50
        touch_event.dy = 50
        touch_event.raw_x = 1500
        touch_event.raw_y = 2500

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "drag"
        assert ui_event.payload["pos"] == (150, 250)
        assert ui_event.payload["dx"] == 50
        assert ui_event.payload["dy"] == 50
        assert ui_event.payload["raw"] == (1500, 2500)

    def test_touch_to_ui_event_swipe(self):
        """Test conversion of swipe touch event to UI event."""
        processor = EventProcessor()

        touch_event = Mock()
        touch_event.type = "swipe"
        touch_event.direction = "left"
        touch_event.dx = -100
        touch_event.dy = 0

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "swipe"
        assert ui_event.payload["direction"] == "left"
        assert ui_event.payload["delta"] == 100

    def test_touch_to_ui_event_press(self):
        """Test conversion of press touch event to UI event."""
        processor = EventProcessor()

        touch_event = Mock()
        touch_event.type = "press"
        touch_event.x = 50
        touch_event.y = 75

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "press"
        assert ui_event.payload["pos"] == (50, 75)

    def test_touch_to_ui_event_release(self):
        """Test conversion of release touch event to UI event."""
        processor = EventProcessor()

        touch_event = Mock()
        touch_event.type = "release"
        touch_event.x = 75
        touch_event.y = 125

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "release"
        assert ui_event.payload["pos"] == (75, 125)

    def test_touch_to_ui_event_unknown_type(self):
        """Test handling of unknown touch event types."""
        processor = EventProcessor()

        touch_event = Mock()
        touch_event.type = "unknown"

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is None

    def test_touch_to_ui_event_missing_attributes(self):
        """Test handling of touch events with missing attributes."""
        processor = EventProcessor()

        # Touch event with no attributes
        touch_event = Mock()
        touch_event.type = "tap"
        # No x, y, raw_x, raw_y attributes

        ui_event = processor.touch_to_ui_event(touch_event)

        assert ui_event is not None
        assert ui_event.type == "tap"
        assert ui_event.payload["pos"] == (None, None)
        assert ui_event.payload["raw"] is None