"""
Application state management for the v2 UI framework.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any

class Track:
    """A simple data class for a single track."""
    def __init__(self, number: int, title: str, artist: Optional[str] = None, artwork: Optional[str] = None):
        self.number = number
        self.title = title
        self.artist = artist
        self.artwork = artwork

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Track:
        return Track(
            number=data.get("number", 0),
            title=data.get("title", "Unknown Title"),
            artist=data.get("artist"),
            artwork=data.get("artwork")
        )

class PlaybackState:
    """Manages the state related to playback."""
    def __init__(self):
        self.playing: bool = False
        self.volume: int = 18
        self.now_playing_track_index: Optional[int] = None
        self.selected_track_index: int = 0
        self.track_scroll_pos: int = 0

class AppState:
    """A centralized class for managing application state."""

    def __init__(self, tracks: List[Dict[str, Any]] = None):
        self.tracks: List[Track] = [Track.from_dict(t) for t in (tracks or [])]
        self.playback = PlaybackState()
        self.artwork_cache: Dict[str, Any] = {}
        self.current_art_thumb: Optional[Any] = None
        self.current_art_path: Optional[str] = None
        self.metadata: Dict[int, Dict[str, Any]] = {}

        # O(1) lookup index: track_number -> track_index
        self._track_number_to_index: Dict[int, int] = self._build_track_index()

    def get_selected_track(self) -> Optional[Track]:
        """Returns the currently selected track."""
        if not self.tracks or not (0 <= self.playback.selected_track_index < len(self.tracks)):
            return None
        return self.tracks[self.playback.selected_track_index]

    def get_now_playing_track(self) -> Optional[Track]:
        """Returns the currently playing track."""
        if self.playback.now_playing_track_index is None or not (0 <= self.playback.now_playing_track_index < len(self.tracks)):
            return None
        return self.tracks[self.playback.now_playing_track_index]

    def set_volume(self, volume: int):
        """Sets the volume, clamped between 0 and 30."""
        self.playback.volume = max(0, min(30, volume))

    def select_track_index(self, index: int) -> Optional[Track]:
        """Selects a track by its index in the list."""
        if not self.tracks:
            return None
        self.playback.selected_track_index = max(0, min(index, len(self.tracks) - 1))
        return self.get_selected_track()

    def start_playback(self, track_index: Optional[int] = None):
        """Starts playback, optionally for a specific track index."""
        if track_index is not None:
            self.playback.now_playing_track_index = track_index
            self.playback.selected_track_index = track_index
        elif self.get_selected_track():
            self.playback.now_playing_track_index = self.playback.selected_track_index
        
        if self.playback.now_playing_track_index is not None:
            self.playback.playing = True

    def stop_playback(self):
        """Stops playback."""
        self.playback.playing = False
        # We keep now_playing_track_index to show the last played track
    
    def pause_playback(self):
        """Pauses playback."""
        self.playback.playing = False

    def advance_track(self, delta: int) -> Optional[Track]:
        """Advances the track selection by a given delta."""
        if not self.tracks:
            return None
        
        current_index = self.playback.now_playing_track_index if self.playback.now_playing_track_index is not None else self.playback.selected_track_index
        if current_index is None:
            current_index = 0
        new_index = (current_index + delta) % len(self.tracks)
        
        self.playback.selected_track_index = new_index
        self.playback.now_playing_track_index = new_index
        
        return self.tracks[new_index]

    def set_tracks(self, tracks: List[Dict[str, Any]]) -> None:
        """Replace the track list with new dictionaries."""
        self.tracks = [Track.from_dict(t) for t in (tracks or [])]
        if not self.tracks:
            self.playback.selected_track_index = 0
            self.playback.now_playing_track_index = None
            return
        if self.playback.selected_track_index is None:
            self.playback.selected_track_index = 0
        self.playback.selected_track_index = min(self.playback.selected_track_index, len(self.tracks) - 1)
        if self.playback.now_playing_track_index is not None and self.playback.now_playing_track_index >= len(self.tracks):
            self.playback.now_playing_track_index = None
        self._apply_metadata_to_tracks()

    def set_metadata(self, metadata: Dict[int, Dict[str, Any]]) -> None:
        """Attach metadata to tracks and cache it for lookups."""
        self.metadata = metadata or {}
        self._apply_metadata_to_tracks()

    def get_track_metadata(self, track_number: int) -> Dict[str, Any]:
        return self.metadata.get(track_number, {})

    def _build_track_index(self) -> Dict[int, int]:
        """
        Build O(1) lookup index mapping track numbers to list indices.

        Returns:
            Dict mapping track.number -> list index
        """
        return {track.number: idx for idx, track in enumerate(self.tracks)}

    def get_index_by_number(self, track_number: int) -> Optional[int]:
        """
        Get track index by track number using O(1) dictionary lookup.

        This method now uses a pre-built dictionary index for O(1) lookups
        instead of O(n) linear search. The index is maintained automatically
        when tracks are modified.

        Args:
            track_number: The track number to look up

        Returns:
            The index in self.tracks list, or None if not found
        """
        return self._track_number_to_index.get(track_number)

    def _apply_metadata_to_tracks(self) -> None:
        if not self.metadata:
            return
        for track in self.tracks:
            meta = self.metadata.get(track.number)
            if not meta:
                continue
            if meta.get("title"):
                track.title = meta["title"]
            if meta.get("artist"):
                track.artist = meta["artist"]
            if meta.get("artwork"):
                track.artwork = meta["artwork"]
