"""Application state management module.

Manages runtime state for playback, tracks, UI, and artwork caching.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Track information."""
    number: int
    title: str
    artist: Optional[str] = None
    artwork_path: Optional[str] = None


@dataclass
class PlaybackState:
    """Current playback state."""
    playing: bool = False
    current_track_number: Optional[int] = None
    current_track_index: Optional[int] = None
    selected_track_index: Optional[int] = None
    now_playing_index: Optional[int] = None
    volume: int = 18


class ApplicationState:
    """Central application state manager.

    Maintains runtime state for all application components including:
    - Track catalog and metadata
    - Playback state
    - UI state (scroll positions, selections)
    - Artwork cache

    Attributes:
        tracks: List of Track objects
        playback: PlaybackState object
        metadata: Dictionary mapping track numbers to metadata
        artwork_cache: LRU cache for album artwork thumbnails
        track_scroll: Current scroll position in track list
    """

    def __init__(self):
        """Initialize application state."""
        self.tracks: List[Track] = []
        self.playback = PlaybackState()
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self.artwork_cache: Dict[str, Any] = {}
        self.track_scroll = 0

        # Current artwork
        self.current_artwork_path: Optional[str] = None
        self.current_artwork_thumb: Optional[Any] = None

        # O(1) lookup index: track_number -> track_index
        self._track_number_to_index: Dict[int, int] = {}

    def set_tracks(self, tracks: List[Track]) -> None:
        """Set track catalog.

        Args:
            tracks: List of Track objects
        """
        self.tracks = tracks
        logger.info(f"Track catalog updated: {len(tracks)} tracks")

        # Rebuild O(1) lookup index
        self._track_number_to_index = self._build_track_index()

        # Apply metadata to tracks if available
        if self.metadata:
            self._apply_metadata_to_tracks()

        # Reset selection if out of bounds
        if self.tracks:
            if self.playback.selected_track_index is None or \
               self.playback.selected_track_index >= len(self.tracks):
                self.playback.selected_track_index = 0
        else:
            self.playback.selected_track_index = None

    def get_track(self, index: int) -> Optional[Track]:
        """Get track by index.

        Args:
            index: Track index in catalog

        Returns:
            Track object or None if invalid index
        """
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def get_track_by_number(self, number: int) -> Optional[Track]:
        """Get track by track number using O(1) lookup.

        Args:
            number: Track number

        Returns:
            Track object or None if not found
        """
        index = self._track_number_to_index.get(number)
        if index is not None:
            return self.get_track(index)
        return None

    def get_index_by_number(self, number: int) -> Optional[int]:
        """Get track index by track number using O(1) lookup.

        This method uses a pre-built dictionary index for O(1) lookups
        instead of O(n) linear search. The index is maintained automatically
        when tracks are modified.

        Args:
            number: Track number

        Returns:
            Track index or None if not found
        """
        return self._track_number_to_index.get(number)

    def get_selected_track(self) -> Optional[Track]:
        """Get currently selected track.

        Returns:
            Track object or None if no selection
        """
        if self.playback.selected_track_index is not None:
            return self.get_track(self.playback.selected_track_index)
        return None

    def get_playing_track(self) -> Optional[Track]:
        """Get currently playing track.

        Returns:
            Track object or None if nothing playing
        """
        if self.playback.now_playing_index is not None:
            return self.get_track(self.playback.now_playing_index)
        return None

    def select_track_index(self, index: int) -> Optional[Track]:
        """Select track by index.

        Args:
            index: Track index

        Returns:
            Selected Track object or None
        """
        if not self.tracks:
            self.playback.selected_track_index = None
            return None

        # Wrap index
        index = index % len(self.tracks)
        self.playback.selected_track_index = index

        track = self.tracks[index]
        self.playback.current_track_number = track.number
        self.playback.current_track_index = index

        logger.debug(f"Selected track {index}: {track.title}")
        return track

    def advance_track(self, delta: int) -> Optional[Track]:
        """Move selection by delta tracks.

        Args:
            delta: Number of tracks to move (+/- integer)

        Returns:
            New selected Track or None
        """
        if not self.tracks:
            return None

        current_idx = self.playback.selected_track_index
        if current_idx is None:
            current_idx = 0

        new_idx = (current_idx + delta) % len(self.tracks)
        return self.select_track_index(new_idx)

    def start_playback(self, track_index: Optional[int] = None) -> None:
        """Start playback at given track index.

        Args:
            track_index: Track index to play (None = use selected)
        """
        if track_index is not None:
            self.select_track_index(track_index)

        self.playback.playing = True
        self.playback.now_playing_index = self.playback.selected_track_index

        track = self.get_playing_track()
        if track:
            logger.info(f"Playback started: {track.title}")

    def pause_playback(self) -> None:
        """Pause playback."""
        self.playback.playing = False
        logger.info("Playback paused")

    def stop_playback(self) -> None:
        """Stop playback."""
        self.playback.playing = False
        self.playback.now_playing_index = None
        logger.info("Playback stopped")

    def set_volume(self, volume: int) -> None:
        """Set volume level.

        Args:
            volume: Volume level (0-30)
        """
        self.playback.volume = max(0, min(30, int(volume)))
        logger.debug(f"Volume set to {self.playback.volume}")

    def set_metadata(self, metadata: Dict[int, Dict[str, Any]]) -> None:
        """Set track metadata dictionary.

        Args:
            metadata: Dictionary mapping track numbers to metadata dicts
        """
        self.metadata = metadata
        logger.info(f"Metadata loaded for {len(metadata)} tracks")

        # Apply metadata to existing tracks
        if self.tracks:
            self._apply_metadata_to_tracks()

    def get_track_metadata(self, track_number: int) -> Dict[str, Any]:
        """Get metadata for track number.

        Args:
            track_number: Track number

        Returns:
            Metadata dictionary (empty if not found)
        """
        return self.metadata.get(track_number, {})

    def cache_artwork(self, path: str, thumbnail: Any) -> None:
        """Cache artwork thumbnail.

        Args:
            path: Artwork file path
            thumbnail: PIL Image thumbnail
        """
        # Simple cache (no size limit for now - can add LRU later)
        self.artwork_cache[path] = thumbnail
        logger.debug(f"Artwork cached: {path}")

    def get_cached_artwork(self, path: str) -> Optional[Any]:
        """Get cached artwork thumbnail.

        Args:
            path: Artwork file path

        Returns:
            PIL Image thumbnail or None
        """
        return self.artwork_cache.get(path)

    def ensure_track_visible(self, index: int, visible_count: int) -> None:
        """Ensure track at index is visible in scrollable list.

        Args:
            index: Track index to make visible
            visible_count: Number of visible rows
        """
        if index < self.track_scroll:
            self.track_scroll = index
        elif index >= self.track_scroll + visible_count:
            self.track_scroll = index - visible_count + 1

        # Clamp scroll position
        max_scroll = max(0, len(self.tracks) - visible_count)
        self.track_scroll = max(0, min(self.track_scroll, max_scroll))

    def _build_track_index(self) -> Dict[int, int]:
        """Build O(1) lookup index mapping track numbers to list indices.

        Returns:
            Dict mapping track.number -> list index
        """
        return {track.number: idx for idx, track in enumerate(self.tracks)}

    def _apply_metadata_to_tracks(self) -> None:
        """Apply metadata to tracks (enrich track objects with metadata).

        Updates track title, artist, and artwork_path from metadata dictionary.
        Called automatically when metadata or tracks are set.
        """
        if not self.metadata:
            return

        for track in self.tracks:
            meta = self.metadata.get(track.number)
            if not meta:
                continue

            # Enrich track with metadata
            if meta.get("title"):
                track.title = meta["title"]
            if meta.get("artist"):
                track.artist = meta["artist"]
            if meta.get("artwork"):
                track.artwork_path = meta["artwork"]

        logger.debug(f"Applied metadata to {len(self.tracks)} tracks")


# Global state instance
_state_instance = None
_state_lock = threading.Lock()


def get_state() -> ApplicationState:
    """Get global application state instance.

    Returns:
        ApplicationState: Global state instance
    """
    global _state_instance

    if _state_instance is None:
        with _state_lock:
            # Double-check locking pattern
            if _state_instance is None:
                _state_instance = ApplicationState()

    return _state_instance
