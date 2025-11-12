"""Configuration management module.

Handles JSON-based configuration persistence for application settings including:
- Touch calibration and orientation
- Volume settings
- UI preferences
- System paths
"""

import json
import logging
import os
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# 8 orientation combos we can cycle through
ORIENTS = [
    dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=False),
    dict(SWAP_XY=False, FLIP_X=True , FLIP_Y=False),
    dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=True ),
    dict(SWAP_XY=False, FLIP_X=True , FLIP_Y=True ),
    dict(SWAP_XY=True , FLIP_X=False, FLIP_Y=False),
    dict(SWAP_XY=True , FLIP_X=True , FLIP_Y=False),
    dict(SWAP_XY=True , FLIP_X=False, FLIP_Y=True ),
    dict(SWAP_XY=True , FLIP_X=True , FLIP_Y=True ),
]

class Config:
    """Centralized configuration manager.

    Provides JSON-based persistence with atomic writes and default values.
    Supports hierarchical configuration with environment variable overrides.

    Attributes:
        config_path: Path to configuration file
        data: Configuration dictionary
    """

    # Default configuration values
    DEFAULTS = {
        "touch": {
            "orientation_index": 6,
            "calibration": None,  # (minx, maxx, miny, maxy) or None
        },
        "audio": {
            "volume": 18,
            "last_backend": "dfplayer",  # "dfplayer" or "spotify"
        },
        "ui": {
            "theme": "default",
            "brightness": 100,
        },
        "paths": {
            "metadata": "/boot/dfplayer_metadata.json",
            "track_catalog": None,
            "artwork_root": None,
        },
        "system": {
            "auto_start": True,
            "log_level": "INFO",
        },
    }

    def __init__(self, config_path=None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file (default: ~/.dfplayer_config.json)
        """
        if config_path is None:
            config_path = os.path.expanduser("~/.dfplayer_config.json")

        self.config_path = config_path
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        """Load config from file or create with defaults.

        Returns:
            Configuration data dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)

                # Merge with defaults (preserve user settings, add new defaults)
                merged = self._deep_merge(self.DEFAULTS.copy(), loaded)
                logger.info(f"Configuration loaded from {self.config_path}")
                return merged

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file: {e}")
                logger.warning("Using default configuration")
                return self.DEFAULTS.copy()
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return self.DEFAULTS.copy()
        else:
            logger.info("No config file found, using defaults")
            return self.DEFAULTS.copy()

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary (defaults)
            overlay: Overlay dictionary (user values)

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path (e.g., "touch.orientation_index")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path (e.g., "touch.orientation_index")
            value: Value to set
        """
        keys = key_path.split('.')
        data = self.data

        # Navigate to parent
        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]

        # Set value
        data[keys[-1]] = value
        logger.debug(f"Config set: {key_path} = {value}")

    def save(self) -> bool:
        """Save configuration to file with atomic write.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(self.config_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Atomic write via temporary file
            tmp_path = self.config_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)

            os.replace(tmp_path, self.config_path)
            logger.info(f"Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def reset(self, section=None):
        """Reset configuration to defaults.

        Args:
            section: Section to reset (None = reset all)
        """
        if section is None:
            self.data = self.DEFAULTS.copy()
            logger.info("Configuration reset to defaults")
        elif section in self.DEFAULTS:
            self.data[section] = self.DEFAULTS[section].copy()
            logger.info(f"Configuration section '{section}' reset to defaults")
        else:
            logger.warning(f"Unknown configuration section: {section}")

    # Convenience methods for common operations

    def get_touch_orientation(self) -> int:
        """Get touch orientation index."""
        return self.get("touch.orientation_index", 6)

    def set_touch_orientation(self, index: int) -> None:
        """Set touch orientation index."""
        self.set("touch.orientation_index", int(index))

    def get_touch_calibration(self) -> Optional[Tuple[int, int, int, int]]:
        """Get touch calibration tuple or None."""
        cal = self.get("touch.calibration")
        if isinstance(cal, (list, tuple)) and len(cal) == 4:
            return tuple(int(v) for v in cal)
        return None

    def set_touch_calibration(self, minx: int, maxx: int, miny: int, maxy: int) -> None:
        """Set touch calibration values."""
        self.set("touch.calibration", [int(minx), int(maxx), int(miny), int(maxy)])

    def clear_touch_calibration(self) -> None:
        """Clear touch calibration."""
        self.set("touch.calibration", None)

    def get_volume(self) -> int:
        """Get volume level."""
        return self.get("audio.volume", 18)

    def set_volume(self, volume: int) -> None:
        """Set volume level."""
        volume = max(0, min(30, int(volume)))
        self.set("audio.volume", volume)

    def get_metadata_path(self) -> Optional[str]:
        """Get metadata file path."""
        # Check environment variable first
        env_path = os.environ.get("DFPLAYER_METADATA")
        if env_path:
            return env_path
        return self.get("paths.metadata", "/boot/dfplayer_metadata.json")

    def get_artwork_root(self) -> Optional[str]:
        """Get artwork root directory."""
        # Check environment variable first
        env_path = os.environ.get("DFPLAYER_ART_ROOT")
        if env_path:
            return env_path
        return self.get("paths.artwork_root")

    def get_track_catalog_path(self) -> Optional[str]:
        """Get track catalog file path."""
        # Check environment variable first
        env_path = os.environ.get("DFPLAYER_TRACK_CATALOG")
        if env_path:
            return env_path
        return self.get("paths.track_catalog")


# Global configuration instance
_config_instance = None
_config_lock = threading.Lock()


def get_config(config_path: Optional[str] = None) -> Config:
    """Get global configuration instance.

    Args:
        config_path: Path to config file (only used on first call)

    Returns:
        Global configuration instance
    """
    global _config_instance

    if _config_instance is None:
        with _config_lock:
            # Double-check locking pattern
            if _config_instance is None:
                _config_instance = Config(config_path)

    return _config_instance
