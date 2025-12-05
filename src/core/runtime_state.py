"""Thread-safe runtime state container for application-level ephemeral data."""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from .application_config import ApplicationConfig

logger = logging.getLogger(__name__)


class RuntimeState:
    """Lightweight, thread-safe store for runtime-only state.

    This is intentionally separate from persisted Config to avoid accidental writes.
    """

    # Valid keys and their expected types for validation
    _VALID_KEYS = {
        "volume": int,
        "ui_theme": str,
        "screen_brightness": int,
        "touch_thresholds": dict,
        "backend": str,
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}

    def hydrate_from_config(self, app_cfg: ApplicationConfig) -> None:
        """Seed runtime state from a typed ApplicationConfig snapshot."""
        with self._lock:
            # Validate and set each value
            self._set_validated("volume", app_cfg.audio.volume)
            self._set_validated("ui_theme", app_cfg.ui_theme)
            self._set_validated("screen_brightness", app_cfg.screen_brightness)
            self._set_validated("touch_thresholds", app_cfg.touch.thresholds)

    def set(self, key: str, value: Any) -> None:
        """Set a runtime value with validation."""
        with self._lock:
            self._set_validated(key, value)

    def _set_validated(self, key: str, value: Any) -> None:
        """Internal setter with type validation (assumes lock is held).

        Raises:
            KeyError: If key is not in _VALID_KEYS schema
            TypeError: If value type doesn't match expected type
            ValueError: If value is out of valid range
        """
        # Validate key is known (strict policy for type safety)
        if key not in self._VALID_KEYS:
            logger.error(f"Attempted to set unknown runtime state key: {key}")
            raise KeyError(f"Unknown runtime state key: {key}. Valid keys: {sorted(self._VALID_KEYS.keys())}")

        # Validate type matches expected
        expected_type = self._VALID_KEYS[key]
        if not isinstance(value, expected_type):
            logger.error(f"Type mismatch for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
            raise TypeError(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")

        # Validate ranges for numeric values
        if key == "volume" and not (0 <= value <= 30):
            logger.error(f"Volume out of range: {value} (expected 0-30)")
            raise ValueError(f"Volume must be between 0 and 30, got {value}")
        if key == "screen_brightness" and not (0 <= value <= 100):
            logger.error(f"Screen brightness out of range: {value} (expected 0-100)")
            raise ValueError(f"Screen brightness must be between 0 and 100, got {value}")

        self._data[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)
