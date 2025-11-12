import builtins
import os

from src.core.profile_select_v3 import detect_profile, select_hardware


def test_detect_env_override(monkeypatch):
    monkeypatch.setenv('DFPLAYER_HW_PROFILE', 'st7735_buttons')
    p = detect_profile(cli_arg=None, env=os.environ, config=None)
    assert p == 'st7735_buttons'


class DummyCfg:
    def __init__(self, val):
        self.val = val
    def get(self, key, default=None):
        if key in ('hardware.profile', 'hardware_profile'):
            return self.val
        return default


def test_detect_config_override():
    cfg = DummyCfg('ili9486_touch')
    p = detect_profile(cli_arg=None, env={}, config=cfg)
    assert p == 'ili9486_touch'


def test_auto_detect_fb_ili9486(monkeypatch):
    # Mock os.path.exists and open
    def fake_exists(path):
        if path == '/sys/class/graphics/fb1/name':
            return True
        return False

    def fake_open(path, mode='r', *args, **kwargs):
        class F:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def read(self):
                return 'ili9486'
        return F()

    monkeypatch.setattr('os.path.exists', fake_exists)
    monkeypatch.setattr(builtins, 'open', fake_open)

    p = detect_profile(cli_arg=None, env={}, config=None)
    assert p == 'ili9486_touch'


def test_auto_detect_hat_waveshare(monkeypatch):
    def fake_exists(path):
        if path in ('/sys/class/graphics/fb1/name',):
            return False
        if path in ('/dev/spidev0.0', '/proc/device-tree/hat/product'):
            return True
        return False

    def fake_open(path, mode='rb', *args, **kwargs):
        class F:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def read(self):
                return b'Waveshare 1.44" LCD HAT\x00'
        return F()

    monkeypatch.setattr('os.path.exists', fake_exists)
    monkeypatch.setattr(builtins, 'open', fake_open)

    p = detect_profile(cli_arg=None, env={}, config=None)
    assert p == 'st7735_buttons'


def test_select_hardware_paths():
    d, i = select_hardware('st7735_buttons')
    assert d.endswith('hardware.display_st7735.DisplayST7735')
    assert i.endswith('hardware.button_input.ButtonInput')
    d, i = select_hardware('ili9486_touch')
    assert d.endswith('hardware.framebuffer.Framebuffer')
    assert i.endswith('hardware.touch.TouchInput')

