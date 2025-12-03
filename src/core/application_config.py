"""Typed application configuration facade built on top of the legacy Config.

This module provides a structured, validated view of configuration data while
remaining backward compatible with the existing `core.config.Config` class.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .config import Config


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


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

        audio_cfg = AudioConfig(
            volume=_clamp(cfg.get_volume(), 0, 30),
            last_track=max(1, int(cfg.get_last_track())),
            auto_play=bool(cfg.get("auto_play", False)),
        )

        paths_cfg = PathsConfig(
            metadata=cfg.get_metadata_path(),
            track_catalog=cfg.get_track_catalog_path(),
            artwork_root=cfg.get_artwork_root(),
        )

        return cls(
            audio=audio_cfg,
            touch=touch_cfg,
            ui_theme=str(cfg.get("ui_theme", "default")),
            screen_brightness=_clamp(cfg.get("screen_brightness", 100), 0, 100),
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
