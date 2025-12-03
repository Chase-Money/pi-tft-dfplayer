import pytest

from src.core.application_config import ApplicationConfig, TouchConfig
from src.core.config import Config
from src.core.runtime_state import RuntimeState
from src.core.service_container import ServiceContainer


def test_application_config_roundtrip(tmp_path):
    cfg = Config(config_path=tmp_path / "cfg.json")
    cfg.reset()
    cfg.set_volume(28)
    cfg.set("last_track", 7)
    cfg.set("auto_play", True)
    cfg.set_touch_calibration(10, 200, 20, 220, validate_range=False)
    cfg.set_touch_orientation(swap_xy=True, flip_x=False, flip_y=True)
    cfg.set_touch_orientation_index(3)
    cfg.set_touch_thresholds(tap_threshold_ms=500, drag_threshold_px=15, swipe_threshold_px=60)
    cfg.set("ui_theme", "neon")
    cfg.set("screen_brightness", 90)

    app_cfg = ApplicationConfig.from_legacy(cfg)
    assert app_cfg.audio.volume == 28
    assert app_cfg.audio.last_track == 7
    assert app_cfg.touch.orientation_index == 3
    assert app_cfg.ui_theme == "neon"
    assert app_cfg.screen_brightness == 90

    # Modify the typed config and apply back to legacy
    app_cfg.audio.volume = 5
    app_cfg.touch.orientation_index = 4
    app_cfg.ui_theme = "retro"
    app_cfg.apply_to_legacy(cfg)

    assert cfg.get_volume() == 5
    assert cfg.get_touch_orientation_index() == 4
    assert cfg.get("ui_theme") == "retro"


def test_touch_config_validation_catches_bad_ranges():
    touch_cfg = TouchConfig(
        calibration={"min_x": 10, "max_x": 5, "min_y": 0, "max_y": 100},
        orientation={"swap_xy": False, "flip_x": False, "flip_y": False},
        orientation_index=0,
        thresholds={"tap_threshold_ms": 400, "drag_threshold_px": 12, "swipe_threshold_px": 48},
    )
    with pytest.raises(ValueError):
        touch_cfg.validate()


def test_runtime_state_hydrates_from_typed_config(tmp_path):
    cfg = Config(config_path=tmp_path / "cfg.json")
    cfg.reset()
    app_cfg = ApplicationConfig.from_legacy(cfg)

    runtime = RuntimeState()
    runtime.hydrate_from_config(app_cfg)
    snap = runtime.snapshot()
    assert snap["volume"] == app_cfg.audio.volume
    assert snap["ui_theme"] == app_cfg.ui_theme
    runtime.set("backend", "dfplayer")
    assert runtime.get("backend") == "dfplayer"


def test_service_container_register_and_require():
    container = ServiceContainer()
    dummy = object()
    container.register("cfg", dummy)
    assert container.require("cfg") is dummy
    with pytest.raises(KeyError):
        container.register("cfg", dummy)
    with pytest.raises(KeyError):
        container.require("missing")
