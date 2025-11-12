"""
Pytest configuration and fixtures for dfplayer tests.
"""
import pytest
import sys
import os
from unittest.mock import Mock

# Mock the evdev module before any tests are collected
# This is necessary because evdev is a Linux-specific library
# and will raise an ImportError on other platforms.
sys.modules['evdev'] = Mock()
sys.modules['evdev.ecodes'] = Mock()
sys.modules['evdev.events'] = Mock()
sys.modules['evdev.uinput'] = Mock()


# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary directory for configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir
