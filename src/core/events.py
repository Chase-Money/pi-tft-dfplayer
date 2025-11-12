"""Event bus module for decoupled component communication.

Implements a simple publish/subscribe event system for application events.
"""

import logging
from collections import defaultdict
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """Simple publish/subscribe event bus.

    Allows components to communicate without direct coupling through
    named events and callbacks.

    Example:
        bus = EventBus()

        def on_track_changed(track_number):
            print(f"Track changed to {track_number}")

        bus.subscribe("track_changed", on_track_changed)
        bus.publish("track_changed", 5)
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable):
        """Subscribe to an event.

        Args:
            event_name: Name of event to subscribe to
            callback: Callback function to invoke when event is published
        """
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
            logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable):
        """Unsubscribe from an event.

        Args:
            event_name: Name of event to unsubscribe from
            callback: Callback function to remove
        """
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)
            logger.debug(f"Unsubscribed from event: {event_name}")

    def publish(self, event_name: str, *args, **kwargs):
        """Publish an event to all subscribers.

        Args:
            event_name: Name of event to publish
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks
        """
        if event_name in self._subscribers:
            logger.debug(f"Publishing event: {event_name} ({len(self._subscribers[event_name])} subscribers)")

            for callback in self._subscribers[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event callback for '{event_name}': {e}")

    def clear(self, event_name: str = None):
        """Clear all subscribers for an event or all events.

        Args:
            event_name: Event to clear (None = clear all events)
        """
        if event_name is None:
            self._subscribers.clear()
            logger.info("All event subscribers cleared")
        elif event_name in self._subscribers:
            del self._subscribers[event_name]
            logger.info(f"Event '{event_name}' subscribers cleared")


# Standard event names
class Events:
    """Standard event name constants."""

    # Playback events
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_STOPPED = "playback_stopped"
    TRACK_CHANGED = "track_changed"
    VOLUME_CHANGED = "volume_changed"

    # UI events
    SCREEN_CHANGED = "screen_changed"
    ORIENTATION_CHANGED = "orientation_changed"
    CALIBRATION_CHANGED = "calibration_changed"

    # Backend events
    BACKEND_SWITCHED = "backend_switched"
    BACKEND_ERROR = "backend_error"

    # Track events
    TRACK_SELECTED = "track_selected"
    TRACKS_LOADED = "tracks_loaded"
    METADATA_LOADED = "metadata_loaded"

    # System events
    CONFIG_SAVED = "config_saved"
    SHUTDOWN = "shutdown"


# Global event bus instance
_event_bus_instance = None


def get_event_bus() -> EventBus:
    """Get global event bus instance.

    Returns:
        EventBus: Global event bus instance
    """
    global _event_bus_instance

    if _event_bus_instance is None:
        _event_bus_instance = EventBus()

    return _event_bus_instance
