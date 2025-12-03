"""Abstract backend interface for music playback.

Defines the common interface that all playback backends must implement.
This allows seamless switching between different music sources (DFPlayer, Spotify, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PlaybackBackend(ABC):
    """Abstract base class for playback backends.

    All playback backends (DFPlayer, Spotify, etc.) must implement this interface
    to ensure consistent control and state management across different sources.

    Attributes:
        name: Human-readable backend name
        is_active: Whether backend is currently active
    """

    def __init__(self, name: str):
        """Initialize playback backend.

        Args:
            name: Human-readable backend name
        """
        self.name = name
        self.is_active = False
        logger.info(f"Backend initialized: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize backend hardware/services.

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown backend and cleanup resources."""
        pass

    @abstractmethod
    def play(self):
        """Start or resume playback."""
        pass

    @abstractmethod
    def pause(self):
        """Pause playback."""
        pass

    @abstractmethod
    def stop(self):
        """Stop playback."""
        pass

    @abstractmethod
    def next_track(self):
        """Skip to next track."""
        pass

    @abstractmethod
    def prev_track(self):
        """Skip to previous track."""
        pass

    @abstractmethod
    def play_track(self, track_id: Any):
        """Play specific track.

        Args:
            track_id: Backend-specific track identifier
        """
        pass

    @abstractmethod
    def set_volume(self, volume: int):
        """Set volume level.

        Args:
            volume: Volume level (0-30 for DFPlayer, may vary by backend)
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current playback status.

        Returns:
            dict: Status dictionary with keys like:
                - playing: bool
                - track_number: int or None
                - volume: int
                - error: str or None
        """
        pass

    @abstractmethod
    def poll_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Fetch a pending asynchronous event from the backend, if any.

        Args:
            timeout: Optional timeout in seconds when waiting for events.

        Returns:
            Event dictionary or None when no events are available.
        """
        pass

    def activate(self):
        """Activate this backend (called when switching to this backend)."""
        self.is_active = True
        logger.info(f"Backend activated: {self.name}")

    def deactivate(self):
        """Deactivate this backend (called when switching away)."""
        self.is_active = False
        logger.info(f"Backend deactivated: {self.name}")

    def __repr__(self):
        """String representation."""
        return f"<{self.__class__.__name__}(name='{self.name}', active={self.is_active})>"
