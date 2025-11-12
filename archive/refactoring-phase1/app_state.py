"""
Centralized state management for the DFPlayer GUI application.
"""

class AppState:
    def __init__(self):
        self.volume = 18
        self.is_playing = False
        self.current_track_number = 1
        self.orientation_index = 6
        self.calibration = None
        self.tracks = []
        self.selected_track_index = 0
        self.now_playing_index = None
        self.track_scroll_position = 0
        self.track_manager = None

    def load_from_config(self, config):
        """Load state from a Config object."""
        self.volume = config.get_volume()
        self.orientation_index = config.get_touch_orientation()
        self.calibration = config.get_touch_calibration()

    def set_track_manager(self, track_manager):
        """Set the track manager and load the tracks."""
        self.track_manager = track_manager
        self.tracks = track_manager.tracks
        if self.tracks:
            self.current_track_number = self.tracks[0]["number"]
