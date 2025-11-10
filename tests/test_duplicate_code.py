"""
Test suite to verify removal of duplicate code.
Ensures single definitions of cal_raw, play_track_index, and init code.
"""
import pytest
import sys
import os
import re
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestDuplicateDefinitions:
    """Test that duplicate code has been removed."""

    def test_cal_raw_defined_once(self):
        """Verify cal_raw is only defined once globally."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Count occurrences of "cal_raw = None"
        pattern = r'^cal_raw\s*=\s*None'
        matches = re.findall(pattern, content, re.MULTILINE)

        assert len(matches) <= 1, \
            f"cal_raw should be defined only once, found {len(matches)} times at lines 35 and 54"

    def test_play_track_index_single_implementation(self):
        """Verify play_track_index has single implementation."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Count function definitions
        pattern = r'^def play_track_index\('
        matches = re.findall(pattern, content, re.MULTILINE)

        assert len(matches) == 1, \
            f"play_track_index should be defined once, found {len(matches)} times"

    def test_play_track_index_returns_boolean(self):
        """Verify play_track_index has proper return statements."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            content = f.read()

        # Find play_track_index function
        pattern = r'def play_track_index\([^)]*\):.*?(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)

        assert match, "play_track_index function should exist"

        func_body = match.group(0)

        # Check for return statements
        assert 'return True' in func_body, "play_track_index should return True on success"
        assert 'return False' in func_body, "play_track_index should return False on failure"

    def test_main_loop_init_not_duplicated(self):
        """Verify main_loop doesn't duplicate initialization code."""
        src_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'dfplayer_fb_gui.py')

        with open(src_file, 'r') as f:
            lines = f.readlines()

        # Find main_loop function
        in_main_loop = False
        duplicate_inits = []

        for i, line in enumerate(lines):
            if 'def main_loop():' in line:
                in_main_loop = True
                continue

            if in_main_loop:
                # Check for duplicate initialization patterns
                if 'touching=False; drag_vol=False' in line.replace(' ', ''):
                    duplicate_inits.append(i + 1)

                # Exit at next function definition
                if line.startswith('def ') and 'main_loop' not in line:
                    break

        # Allow one initialization, flag duplicates
        assert len(duplicate_inits) <= 1, \
            f"Duplicate initialization found at lines: {duplicate_inits}"
