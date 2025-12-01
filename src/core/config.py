"""
Config: canonical configuration manager for the application stack.

Provides thread-safe loading and saving of user preferences and system state
to ~/.dfplayer_config.json with atomic writes and validation.
"""

import copy
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional
from .orients import ORIENTS  # backwards compat

logger = logging.getLogger(__name__)


def _validate_path(path: str, allowed_prefixes: List[str]) -> Optional[str]:
    """
    Validate a file path to prevent directory traversal and restrict to allowed directories.

    This function provides security against path traversal attacks by:
    - Rejecting paths with ".." components
    - Rejecting paths with suspicious characters
    - Ensuring resolved paths start with one of the allowed prefixes
    - Resolving symlinks to detect traversal attempts

    Args:
        path: Path to validate (can be relative or absolute)
        allowed_prefixes: List of allowed directory prefixes (e.g., ["/boot/", "/home/pi/"])

    Returns:
        Validated absolute path if safe, None if path is rejected

    Examples:
        >>> _validate_path("/boot/metadata.json", ["/boot/"])
        '/boot/metadata.json'
        >>> _validate_path("../../../etc/passwd", ["/boot/"])
        None
        >>> _validate_path("/home/pi/../../../etc/shadow", ["/home/pi/"])
        None
    """
    if not path or not isinstance(path, str):
        return None

    try:
        # Reject paths with suspicious characters
        suspicious_patterns = [
            r'\x00',  # Null bytes
            r'[\x01-\x1f]',  # Control characters
        ]
        for pattern in suspicious_patterns:
            if re.search(pattern, path):
                logger.warning(f"Path contains suspicious characters: {path}")
                return None

        # Resolve to absolute path (also resolves symlinks)
        resolved_path = Path(path).resolve()
        abs_path_str = str(resolved_path)

        # Normalize allowed prefixes to absolute paths
        normalized_prefixes = []
        for prefix in allowed_prefixes:
            try:
                normalized_prefix = str(Path(prefix).resolve())
                # Ensure prefix ends with separator for proper prefix matching
                if not normalized_prefix.endswith(os.sep):
                    normalized_prefix += os.sep
                normalized_prefixes.append(normalized_prefix)
            except Exception as e:
                logger.error(f"Invalid allowed prefix {prefix}: {e}")
                continue

        if not normalized_prefixes:
            logger.error("No valid allowed prefixes provided")
            return None

        # Check if resolved path starts with any allowed prefix
        path_matches = False
        for prefix in normalized_prefixes:
            # Check if path is within prefix directory
            if abs_path_str.startswith(prefix) or abs_path_str + os.sep == prefix:
                path_matches = True
                break

        if not path_matches:
            logger.warning(
                f"Path outside allowed directories: {path} -> {abs_path_str}\n"
                f"Allowed prefixes: {allowed_prefixes}"
            )
            return None

        logger.debug(f"Path validated successfully: {path} -> {abs_path_str}")
        return abs_path_str

    except Exception as e:
        logger.error(f"Error validating path {path}: {e}")
        return None


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

    # Security: Allowed directories for file paths from environment variables
    # This whitelist prevents path traversal attacks
    ALLOWED_METADATA_PREFIXES = ["/boot/", "/home/pi/", str(Path.home())]
    ALLOWED_ARTWORK_PREFIXES = ["/boot/", "/home/pi/", "/media/", "/mnt/", str(Path.home())]
    ALLOWED_CATALOG_PREFIXES = ["/boot/", "/home/pi/", str(Path.home())]
    TOUCH_THRESHOLD_DEFAULTS = {
        "tap_threshold_ms": 400,  # Max time for tap (ms)
        "drag_threshold_px": 12,  # Min pixels for drag
        "swipe_threshold_px": 70,  # Min pixels for swipe (increased to reduce accidental swipes)
        "tap_debounce_ms": 100,  # Min time between taps to prevent double-tap (ms)
    }

    # Calibration screen defaults
    # - Configurable to support different screen sizes and hardware constraints
    # - Adaptive sizing scales based on screen dimensions for better UX on small displays
    CALIBRATION_DEFAULTS = {
        "target_offset_px": 40,      # Distance from screen edges for calibration targets
        "samples_per_target": 3,     # Number of samples to collect per target for median filtering
        "target_radius_px": 18,      # Visual radius of calibration target circles
        "adaptive_sizing": True,     # Scale target offset based on screen size
    }

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
        "touch_thresholds": TOUCH_THRESHOLD_DEFAULTS,
        "calibration": CALIBRATION_DEFAULTS,
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
                try:
                    os.chmod(self.config_path, 0o600)
                except Exception as chmod_exc:
                    logger.error(f"Unable to set config permissions to 600: {chmod_exc}")
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
        Recursively merge override into base (dicts only; lists are replaced, not merged).

        WARNING: This merge strategy does NOT merge lists - it replaces them entirely.
        If the base config contains a list and the override also provides a value for
        that key, the entire list from base is discarded and replaced with override's value.

        Example demonstrating the limitation:
            base = {"features": ["feature_a", "feature_b"], "settings": {"theme": "dark"}}
            override = {"features": ["feature_c"], "settings": {"volume": 20}}
            result = {"features": ["feature_c"], "settings": {"theme": "dark", "volume": 20}}
            # Note: "feature_a" and "feature_b" are lost

        For more sophisticated list merging (append, prepend, deduplicate), consider
        using a library like `deepmerge` or implementing custom merge logic.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary where nested dicts are recursively merged,
            but all other types (including lists) are replaced
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

    def set_touch_calibration(
        self,
        min_x: int,
        max_x: int,
        min_y: int,
        max_y: int,
        *,
        validate_range: bool = True,
        adc_min: int = 0,
        adc_max: int = 4095,
    ) -> None:
        """
        Set touch calibration parameters.

        Args:
            min_x: Minimum X coordinate
            max_x: Maximum X coordinate
            min_y: Minimum Y coordinate
            max_y: Maximum Y coordinate

        Raises:
            ValueError: If min >= max for either axis or values are out of expected range
        """
        if min_x >= max_x:
            raise ValueError(f"Invalid X calibration: min_x ({min_x}) must be < max_x ({max_x})")
        if min_y >= max_y:
            raise ValueError(f"Invalid Y calibration: min_y ({min_y}) must be < max_y ({max_y})")

        if validate_range:
            # Optional sanity bounds for typical panels; allow override for other hardware
            for val, axis in ((min_x, "min_x"), (max_x, "max_x"), (min_y, "min_y"), (max_y, "max_y")):
                if val < adc_min or val > adc_max:
                    raise ValueError(f"Calibration {axis} ({val}) out of expected range {adc_min}-{adc_max}")

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
        """
        Get metadata file path with env override and security validation.

        Returns:
            Validated metadata file path, or None if validation fails
        """
        env_path = os.environ.get("DFPLAYER_METADATA")
        if env_path:
            validated = _validate_path(env_path, self.ALLOWED_METADATA_PREFIXES)
            if validated:
                return validated
            else:
                logger.error(
                    f"DFPLAYER_METADATA environment variable rejected: {env_path}\n"
                    f"Path must be within: {self.ALLOWED_METADATA_PREFIXES}"
                )
                # Fall through to config file path

        config_path = self.get("paths", {}).get("metadata", self.DEFAULT_VALUES["paths"]["metadata"])
        if config_path:
            validated = _validate_path(config_path, self.ALLOWED_METADATA_PREFIXES)
            if validated:
                return validated
            else:
                logger.warning(f"Config metadata path rejected: {config_path}")
                return None
        return None

    def get_artwork_root(self) -> Optional[str]:
        """
        Get artwork root directory with env override and security validation.

        Returns:
            Validated artwork root directory path, or None if validation fails
        """
        env_path = os.environ.get("DFPLAYER_ART_ROOT")
        if env_path:
            validated = _validate_path(env_path, self.ALLOWED_ARTWORK_PREFIXES)
            if validated:
                return validated
            else:
                logger.error(
                    f"DFPLAYER_ART_ROOT environment variable rejected: {env_path}\n"
                    f"Path must be within: {self.ALLOWED_ARTWORK_PREFIXES}"
                )
                # Fall through to config file path

        config_path = self.get("paths", {}).get("artwork_root", None)
        if config_path:
            validated = _validate_path(config_path, self.ALLOWED_ARTWORK_PREFIXES)
            if validated:
                return validated
            else:
                logger.warning(f"Config artwork root rejected: {config_path}")
                return None
        return None

    def get_track_catalog_path(self) -> Optional[str]:
        """
        Get track catalog file path with env override and security validation.

        Returns:
            Validated track catalog file path, or None if validation fails
        """
        env_path = os.environ.get("DFPLAYER_TRACK_CATALOG")
        if env_path:
            validated = _validate_path(env_path, self.ALLOWED_CATALOG_PREFIXES)
            if validated:
                return validated
            else:
                logger.error(
                    f"DFPLAYER_TRACK_CATALOG environment variable rejected: {env_path}\n"
                    f"Path must be within: {self.ALLOWED_CATALOG_PREFIXES}"
                )
                # Fall through to config file path

        config_path = self.get("paths", {}).get("track_catalog", None)
        if config_path:
            validated = _validate_path(config_path, self.ALLOWED_CATALOG_PREFIXES)
            if validated:
                return validated
            else:
                logger.warning(f"Config track catalog rejected: {config_path}")
                return None
        return None

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
        tap_threshold_ms: Optional[int] = None,
        drag_threshold_px: Optional[int] = None,
        swipe_threshold_px: Optional[int] = None
    ) -> None:
        """Set touch gesture threshold parameters."""
        defaults = self.DEFAULT_VALUES["touch_thresholds"]
        self.set("touch_thresholds", {
            "tap_threshold_ms": max(0, tap_threshold_ms if tap_threshold_ms is not None else defaults["tap_threshold_ms"]),
            "drag_threshold_px": max(0, drag_threshold_px if drag_threshold_px is not None else defaults["drag_threshold_px"]),
            "swipe_threshold_px": max(0, swipe_threshold_px if swipe_threshold_px is not None else defaults["swipe_threshold_px"])
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
