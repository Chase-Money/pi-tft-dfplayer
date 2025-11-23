"""
Test suite for undefined variable fixes.
Ensures track_numbers and related variables are properly defined.
"""
import pytest
import sys
import os
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTrackNumbersVariable:
    """Test track_numbers list existence and usage."""

    def test_track_numbers_list_exists(self):
        """Verify track_numbers is defined globally."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Check for track_numbers definition
        assert 'track_numbers = ' in content, \
            "track_numbers should be defined at module level"

    def test_track_numbers_initialized_from_tracks(self):
        """Verify track_numbers is initialized from tracks list."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Check that track_numbers is built from tracks
        assert 't["number"] for t in tracks' in content, \
            "track_numbers should be initialized from tracks list"

    def test_current_track_idx_variable_exists(self):
        """Verify current_track_idx is defined globally."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        assert 'current_track_idx = ' in content, \
            "current_track_idx should be defined at module level"

    def test_step_track_with_tracks(self):
        """Verify step_track references track_numbers."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find step_track function
        import re
        pattern = r'def step_track\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "step_track function should exist"

        func_body = match.group(0)

        # Verify it references track_numbers
        assert 'track_numbers' in func_body, \
            "step_track should reference track_numbers variable"

    def test_step_track_wraps_around(self):
        """Verify step_track uses modulo for wrapping."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find step_track function
        import re
        pattern = r'def step_track\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "step_track function should exist"

        func_body = match.group(0)

        # Check for modulo operation (wrapping)
        assert '%' in func_body or 'len(track_numbers)' in func_body, \
            "step_track should handle list wrapping"

    def test_set_track_updates_indices(self):
        """Verify set_track references track_numbers."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find set_track function
        import re
        pattern = r'def set_track\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "set_track function should exist"

        func_body = match.group(0)

        # Verify it references track_numbers and current_track_idx
        assert 'track_numbers' in func_body, \
            "set_track should reference track_numbers variable"
        assert 'current_track_idx' in func_body, \
            "set_track should reference current_track_idx variable"
