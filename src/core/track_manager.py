"""
Track management for the DFPlayer GUI.
"""

from typing import List, Dict, Any, Optional
from utils.track_catalog import load_track_catalog
from core.state import Track

class TrackManager:
    """Manages track catalog with dict-based interface for backward compatibility.

    This class wraps the track_catalog utility and provides dict-based track
    representation for legacy code compatibility.
    """

    def __init__(self, config):
        """Initialize track manager.

        Args:
            config: Config object with get_track_catalog_path() method
        """
        self.config = config
        catalog_path = self.config.get_track_catalog_path()

        # Load tracks using the shared utility
        track_objects: List[Track] = load_track_catalog(catalog_path, fallback_count=30)

        # Convert Track objects to dict format for backward compatibility
        self.tracks: List[Dict[str, Any]] = [
            {"number": t.number, "title": t.title}
            for t in track_objects
        ]
        self.track_numbers = [t["number"] for t in self.tracks]

    def get_track_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """Get a track by its index in the list.

        Args:
            index: Zero-based track index

        Returns:
            Track dict or None if index is invalid
        """
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def get_track_by_number(self, track_number: int) -> Optional[Dict[str, Any]]:
        """Get a track by its number.

        Args:
            track_number: Track number to find

        Returns:
            Track dict or None if not found
        """
        for track in self.tracks:
            if track["number"] == track_number:
                return track
        return None
