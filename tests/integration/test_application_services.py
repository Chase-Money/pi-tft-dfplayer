import types

import pytest


def test_application_wires_typed_config_and_services(monkeypatch):
    captured = {}

    class DummyFramebuffer:
        width = 480
        height = 320

        def __init__(self, *args, **kwargs):
            captured["fb_init"] = True

        def push(self, image):
            captured["fb_push"] = True

        def close(self):
            captured["fb_close"] = True

    class DummyTouch:
        available = True

        def __init__(self, config=None):
            captured["touch_cfg"] = config

        def set_calibration(self, *args, **kwargs):
            captured["calibration_set"] = args

        def set_orientation(self, **kwargs):
            captured["orientation_set"] = kwargs

        def get_events(self, timeout=0):
            captured["touch_events_called"] = True
            return []

    class DummyBackend:
        def __init__(self, *args, **kwargs):
            captured["backend_init"] = True
            self.volume_set = None

        def initialize(self):
            captured["backend_initialize"] = True
            return True

        def set_volume(self, volume):
            self.volume_set = volume
            captured["backend_volume"] = volume

        def poll_event(self, timeout=0):
            return None

        def get_status(self):
            return {"dropped_events": 0}

        def shutdown(self):
            captured["backend_shutdown"] = True

    def fake_load_catalog(path):
        captured["catalog_path"] = path
        return []

    def fake_load_metadata(meta_path, art_root):
        captured["metadata_paths"] = (meta_path, art_root)
        return {}

    monkeypatch.setenv("DFPLAYER_METADATA", "/boot/dfplayer_metadata.json")
    monkeypatch.setenv("DFPLAYER_TRACK_CATALOG", "/boot/catalog.json")
    monkeypatch.setenv("DFPLAYER_ART_ROOT", "/boot/art")

    monkeypatch.setattr("hardware.framebuffer.Framebuffer", DummyFramebuffer)
    monkeypatch.setattr("hardware.touch_controller.TouchController", DummyTouch)
    monkeypatch.setattr("backends.dfplayer.DFPlayerBackend", DummyBackend)
    monkeypatch.setattr("utils.track_catalog.load_track_catalog", fake_load_catalog)
    monkeypatch.setattr("utils.metadata.load_metadata", fake_load_metadata)

    # Avoid entering the main loop by patching ScreenManagerV2.render
    class DummySM:
        def __init__(self, services=None):
            self.services = services or {}

        def register(self, *args, **kwargs):
            pass

        def push(self, *args, **kwargs):
            pass

        def handle_event(self, *args, **kwargs):
            pass

        def render(self, *args, **kwargs):
            pass

    monkeypatch.setattr("ui.framework.manager.ScreenManagerV2", DummySM)
    monkeypatch.setattr("ui.renderer.FramebufferRendererV2.present", lambda self: None)
    monkeypatch.setattr("ui.renderer.FramebufferRendererV2.render", lambda self: None)

    from app import Application

    app = Application()

    # Services should include typed config and runtime state
    assert "app_config" in app.screen_manager.services
    assert "runtime_state" in app.screen_manager.services

    # Volume should be applied from typed config defaults
    assert captured["backend_volume"] == app.app_config.audio.volume

    # Paths should come from env overrides via Config validation
    assert captured["catalog_path"] == "/boot/catalog.json"
    assert captured["metadata_paths"] == ("/boot/dfplayer_metadata.json", "/boot/art")

    # Cleanup should call backend shutdown and framebuffer close safely
    app.cleanup()
    assert captured.get("backend_shutdown")
    assert captured.get("fb_close")
