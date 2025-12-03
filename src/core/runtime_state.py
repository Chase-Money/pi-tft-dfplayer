"""Thread-safe runtime state container for application-level ephemeral data."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from .application_config import ApplicationConfig


class RuntimeState:
    """Lightweight, thread-safe store for runtime-only state.

    This is intentionally separate from persisted Config to avoid accidental writes.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}

    def hydrate_from_config(self, app_cfg: ApplicationConfig) -> None:
        """Seed runtime state from a typed ApplicationConfig snapshot."""
        with self._lock:
            self._data.update(
                {
                    "volume": app_cfg.audio.volume,
                    "ui_theme": app_cfg.ui_theme,
                    "screen_brightness": app_cfg.screen_brightness,
                    "touch_thresholds": app_cfg.touch.thresholds,
                }
            )

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)
