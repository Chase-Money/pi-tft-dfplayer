"""
ConfigV2: canonical configuration manager for the v2 application stack.

Provides thread-safe loading and saving of user preferences and system state
to ~/.dfplayer_config.json with atomic writes and validation.
"""

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional
from .orients import ORIENTS  # backwards compat

logger = logging.getLogger(__name__)


class Config:
    """
    Thread-safe configuration manager with atomic persistence.

    Stores user preferences and application state including:
    - Touch calibration parameters
    - Touch orientation settings
    - Volume level
    - Last played track
    - UI theme and preferences
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".dfplayer_config.json"

    DEFAULT_VALUES = {
        "volume": 15,
        "last_track": 1,
        "touch_calibration": {
            "min_x": 0,
            "max_x": 4095,
            "min_y": 0,
            "max_y": 4095
        },
        "touch_orientation": {
            "swap_xy": False,
            "flip_x": False,
            "flip_y": False
        },
        "touch_orientation_index": 6,
        "touch_thresholds": {
            "tap_threshold_ms": 400,  # Max time for tap (ms)
            "drag_threshold_px": 12,  # Min pixels for drag
            "swipe_threshold_px": 48  # Min pixels for swipe
        },
        "ui_theme": "default",
        "screen_brightness": 100,
        "auto_play": False,
        "paths": {
            "metadata": "/boot/dfplayer_metadata.json",
            "track_catalog": None,
            "artwork_root": None,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file (default: ~/.dfplayer_config.json)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._data: Dict[str, Any] = {}
        self._lock = RLock()  # Reentrant lock for thread safety
        self._loaded = False

    def load(self) -> bool:
        """
        Load configuration from disk.

        Returns:
            True if loaded successfully, False if using defaults
        """
        with self._lock:
            try:
                if not self.config_path.exists():
                    logger.info(f"Config file not found at {self.config_path}, using defaults")
                    self._data = copy.deepcopy(self.DEFAULT_VALUES)
                    self._loaded = True
                    return False

                with open(self.config_path, 'r') as f:
                    loaded_data = json.load(f)

                # Validate loaded data
                if not isinstance(loaded_data, dict):
                    logger.error("Config file is not a valid JSON object, using defaults")
                    self._data = copy.deepcopy(self.DEFAULT_VALUES)
                    return False

                # Merge with defaults (in case new keys were added)
                self._data = self._merge_with_defaults(loaded_data)
                # Ensure required defaults are present even if the file has empty dicts
                for key, val in self.DEFAULT_VALUES.items():
                    if key not in self._data or (isinstance(self._data[key], dict) and not self._data[key]):
                        self._data[key] = val
                self._loaded = True
                logger.info(f"Configuration loaded from {self.config_path}")
                return True

            except json.JSONDecodeError as e:
                logger.error(f"Config file is corrupted: {e}, using defaults")
                self._data = copy.deepcopy(self.DEFAULT_VALUES)
                self._loaded = True
                # Backup corrupted file
                self._backup_corrupted_config()
                return False

            except Exception as e:
                logger.error(f"Error loading config: {e}, using defaults")
                self._data = copy.deepcopy(self.DEFAULT_VALUES)
                self._loaded = True
                return False

    def save(self) -> bool:
        """
        Save configuration to disk using atomic write.

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            try:
                # Ensure config directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)

                # Atomic write: write to temp file, then rename
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    dir=self.config_path.parent,
                    delete=False,
                    suffix='.tmp'
                ) as tmp_file:
                    json.dump(self._data, tmp_file, indent=2)
                    tmp_path = tmp_file.name

                # Atomic rename
                os.replace(tmp_path, self.config_path)
                logger.info(f"Configuration saved to {self.config_path}")
                return True

            except Exception as e:
                logger.error(f"Error saving config: {e}")
                # Clean up temp file if it exists
                try:
                    if 'tmp_path' in locals():
                        os.unlink(tmp_path)
                except Exception:
                    pass
                return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        with self._lock:
            # Lazy load if not loaded yet
            if not self._loaded:
                self.load()

            # Support dot notation (e.g., "touch_calibration.min_x")
            keys = key.split('.')
            value = self._data

            # Special-case touch_thresholds to guarantee defaults
            if key == "touch_thresholds":
                val = self._data.get("touch_thresholds")
                if not isinstance(val, dict) or not val:
                    return self.DEFAULT_VALUES["touch_thresholds"].copy()
                merged = self.DEFAULT_VALUES["touch_thresholds"].copy()
                merged.update(val)
                return merged

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    value = default
                    break

            if key == "touch_thresholds" and (not value or not isinstance(value, dict)):
                return self.DEFAULT_VALUES["touch_thresholds"]

            return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        with self._lock:
            # Lazy load if not loaded yet
            if not self._loaded:
                self.load()

            # Support dot notation (e.g., "touch_calibration.min_x")
            keys = key.split('.')

            if len(keys) == 1:
                self._data[key] = value
            else:
                # Navigate to nested dict
                current = self._data
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration data.

        Returns:
            Copy of configuration dictionary
        """
        with self._lock:
            if not self._loaded:
                self.load()
            return self._data.copy()

    def reset(self) -> None:
        """Reset configuration to default values."""
        with self._lock:
            self._data = copy.deepcopy(self.DEFAULT_VALUES)
            logger.info("Configuration reset to defaults")

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """
        Recursively merge override into base.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        merged = base.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = Config._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _merge_with_defaults(self, loaded_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded data with defaults.

        Args:
            loaded_data: Data loaded from file

        Returns:
            Merged configuration
        """
        result = copy.deepcopy(self.DEFAULT_VALUES)
        return self._deep_merge(result, loaded_data)

    def _backup_corrupted_config(self) -> None:
        """Create backup of corrupted config file."""
        try:
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.corrupted')
                self.config_path.rename(backup_path)
                logger.info(f"Corrupted config backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted config: {e}")

    # Convenience methods for common settings

    def get_volume(self) -> int:
        """Get volume level (0-30)."""
        return int(self.get("volume", 15))

    def set_volume(self, volume: int) -> None:
        """Set volume level (0-30)."""
        self.set("volume", max(0, min(30, volume)))

    def get_touch_calibration(self) -> Dict[str, int]:
        """Get touch calibration parameters."""
        return self.get("touch_calibration", self.DEFAULT_VALUES["touch_calibration"])

    def set_touch_calibration(self, min_x: int, max_x: int, min_y: int, max_y: int) -> None:
        """Set touch calibration parameters."""
        self.set("touch_calibration", {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y
        })

    def get_touch_orientation(self) -> Dict[str, bool]:
        """Get touch orientation settings."""
        return self.get("touch_orientation", self.DEFAULT_VALUES["touch_orientation"])

    def set_touch_orientation(self, swap_xy: bool = False, flip_x: bool = False, flip_y: bool = False) -> None:
        """Set touch orientation settings."""
        self.set("touch_orientation", {
            "swap_xy": swap_xy,
            "flip_x": flip_x,
            "flip_y": flip_y
        })

    def get_touch_orientation_index(self) -> int:
        """Get touch orientation index (legacy compatibility)."""
        return int(self.get("touch_orientation_index", self.DEFAULT_VALUES.get("touch_orientation_index", 0)))

    def set_touch_orientation_index(self, index: int) -> None:
        """Set touch orientation index (legacy compatibility)."""
        self.set("touch_orientation_index", int(index))

    def get_metadata_path(self) -> Optional[str]:
        """Get metadata file path with env override."""
        env_path = os.environ.get("DFPLAYER_METADATA")
        if env_path:
            return env_path
        return self.get("paths", {}).get("metadata", self.DEFAULT_VALUES["paths"]["metadata"])

    def get_artwork_root(self) -> Optional[str]:
        """Get artwork root directory with env override."""
        env_path = os.environ.get("DFPLAYER_ART_ROOT")
        if env_path:
            return env_path
        return self.get("paths", {}).get("artwork_root", None)

    def get_track_catalog_path(self) -> Optional[str]:
        """Get track catalog file path with env override."""
        env_path = os.environ.get("DFPLAYER_TRACK_CATALOG")
        if env_path:
            return env_path
        return self.get("paths", {}).get("track_catalog", None)

    def get_touch_thresholds(self) -> Dict[str, int]:
        """Get touch gesture threshold parameters."""
        thresholds = self.get("touch_thresholds", self.DEFAULT_VALUES["touch_thresholds"])
        # Backfill missing keys or empty dicts
        if not thresholds:
            thresholds = self.DEFAULT_VALUES["touch_thresholds"].copy()
        else:
            for k, v in self.DEFAULT_VALUES["touch_thresholds"].items():
                thresholds.setdefault(k, v)
        return thresholds

    def set_touch_thresholds(
        self,
        tap_threshold_ms: int = 800,
        drag_threshold_px: int = 80,
        swipe_threshold_px: int = 120
    ) -> None:
        """Set touch gesture threshold parameters."""
        self.set("touch_thresholds", {
            "tap_threshold_ms": max(0, tap_threshold_ms),
            "drag_threshold_px": max(0, drag_threshold_px),
            "swipe_threshold_px": max(0, swipe_threshold_px)
        })

    def get_last_track(self) -> int:
        """Get last played track number."""
        return int(self.get("last_track", 1))

    def set_last_track(self, track_number: int) -> None:
        """Set last played track number."""
        self.set("last_track", max(1, track_number))


# Singleton instance for global access
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config singleton instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
        _config_instance.load()
    return _config_instance
