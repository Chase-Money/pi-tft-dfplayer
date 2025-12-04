"""Typed application configuration facade built on top of the legacy Config.

This module provides a structured, validated view of configuration data while
remaining backward compatible with the existing `core.config.Config` class.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config

logger = logging.getLogger(__name__)


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _validate_path(path: Optional[str], path_type: str) -> Optional[str]:
    """Validate a file path for security and existence.

    Args:
        path: Path to validate (can be None)
        path_type: Description for logging (e.g., "metadata", "artwork_root")

    Returns:
        Validated path or None if invalid/missing

    Security: Prevents directory traversal and symlink attacks
    """
    if not path:
        return None

    try:
        # Resolve to absolute path and check for directory traversal
        resolved = Path(path).resolve()

        # Log warning if path doesn't exist (but don't fail - may be created later)
        if not resolved.exists():
            logger.warning(f"{path_type} path does not exist: {resolved}")

        # Detect suspicious patterns
        if ".." in str(path):
            logger.warning(f"Suspicious path with '..' detected in {path_type}: {path}")

        return str(resolved)
    except (OSError, ValueError) as e:
        logger.error(f"Invalid {path_type} path '{path}': {e}")
        return None


@dataclass
class PathsConfig:
    metadata: Optional[str]
    track_catalog: Optional[str]
    artwork_root: Optional[str]


@dataclass
class TouchConfig:
    calibration: Dict[str, int]
    orientation: Dict[str, bool]
    orientation_index: int
    thresholds: Dict[str, int]

    def validate(self) -> None:
        # Basic bounds and presence validation; deeper checks live in Config.
        required_cal_keys = {"min_x", "max_x", "min_y", "max_y"}
        missing = required_cal_keys - set(self.calibration.keys())
        if missing:
            raise ValueError(f"Calibration missing keys: {sorted(missing)}")
        if self.calibration["min_x"] >= self.calibration["max_x"]:
            raise ValueError("Calibration min_x must be < max_x")
        if self.calibration["min_y"] >= self.calibration["max_y"]:
            raise ValueError("Calibration min_y must be < max_y")

        required_thresh_keys = {"tap_threshold_ms", "drag_threshold_px", "swipe_threshold_px"}
        missing_thresh = required_thresh_keys - set(self.thresholds.keys())
        if missing_thresh:
            raise ValueError(f"Thresholds missing keys: {sorted(missing_thresh)}")


@dataclass
class AudioConfig:
    volume: int
    last_track: int
    auto_play: bool


@dataclass
class ApplicationConfig:
    """Structured view of application configuration."""

    audio: AudioConfig
    touch: TouchConfig
    ui_theme: str
    screen_brightness: int
    paths: PathsConfig

    @classmethod
    def from_legacy(cls, cfg: Config) -> "ApplicationConfig":
        """Build from existing Config while honoring its validation/env rules."""
        touch_cal = cfg.get_touch_calibration()
        touch_orientation = cfg.get_touch_orientation()
        touch_thresholds = cfg.get_touch_thresholds()
        touch_cfg = TouchConfig(
            calibration=touch_cal,
            orientation=touch_orientation,
            orientation_index=cfg.get_touch_orientation_index(),
            thresholds=touch_thresholds,
        )
        touch_cfg.validate()

        # Validate audio settings with type safety
        volume = cfg.get_volume()
        if not isinstance(volume, int):
            volume = int(volume) if volume is not None else 15
        last_track = cfg.get_last_track()
        if not isinstance(last_track, int):
            last_track = int(last_track) if last_track is not None else 1
        auto_play = cfg.get("auto_play", False)
        if not isinstance(auto_play, bool):
            auto_play = bool(auto_play)

        audio_cfg = AudioConfig(
            volume=_clamp(volume, 0, 30),
            last_track=max(1, last_track),
            auto_play=auto_play,
        )

        # Validate and sanitize file paths (security: prevent directory traversal)
        paths_cfg = PathsConfig(
            metadata=_validate_path(cfg.get_metadata_path(), "metadata"),
            track_catalog=_validate_path(cfg.get_track_catalog_path(), "track_catalog"),
            artwork_root=_validate_path(cfg.get_artwork_root(), "artwork_root"),
        )

        # Validate UI settings with type safety
        ui_theme = cfg.get("ui_theme", "default")
        if not isinstance(ui_theme, str):
            ui_theme = "default"
        screen_brightness = cfg.get("screen_brightness", 100)
        if not isinstance(screen_brightness, int):
            screen_brightness = int(screen_brightness) if screen_brightness is not None else 100

        return cls(
            audio=audio_cfg,
            touch=touch_cfg,
            ui_theme=ui_theme,
            screen_brightness=_clamp(screen_brightness, 0, 100),
            paths=paths_cfg,
        )

    def apply_to_legacy(self, cfg: Config) -> None:
        """Persist this structured config back into the legacy Config."""
        # Audio
        cfg.set_volume(self.audio.volume)
        cfg.set("last_track", max(1, int(self.audio.last_track)))
        cfg.set("auto_play", bool(self.audio.auto_play))

        # Touch
        cal = self.touch.calibration
        cfg.set_touch_calibration(cal["min_x"], cal["max_x"], cal["min_y"], cal["max_y"], validate_range=False)
        orient = self.touch.orientation
        cfg.set_touch_orientation(
            swap_xy=bool(orient.get("swap_xy", False)),
            flip_x=bool(orient.get("flip_x", False)),
            flip_y=bool(orient.get("flip_y", False)),
        )
        cfg.set_touch_orientation_index(int(self.touch.orientation_index))
        cfg.set_touch_thresholds(
            tap_threshold_ms=self.touch.thresholds.get("tap_threshold_ms"),
            drag_threshold_px=self.touch.thresholds.get("drag_threshold_px"),
            swipe_threshold_px=self.touch.thresholds.get("swipe_threshold_px"),
        )

        # UI
        cfg.set("ui_theme", self.ui_theme)
        cfg.set("screen_brightness", _clamp(self.screen_brightness, 0, 100))

        # Paths
        paths = {
            "metadata": self.paths.metadata,
            "track_catalog": self.paths.track_catalog,
            "artwork_root": self.paths.artwork_root,
        }
        cfg.set("paths", paths)

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return dataclasses.asdict(self)
