def test_bootstrap_aliases_installs_v2_modules():
    from src.main_touch_v2 import bootstrap_aliases
    mapping = bootstrap_aliases()

    assert 'utils.calibration' in mapping
    assert 'utils.track_catalog' in mapping
    assert 'backends.dfplayer_backend' in mapping

    import sys
    # Proxies are ModuleType instances; we avoid importing heavy deps in tests
    assert sys.modules['utils.calibration'].__class__.__name__ == 'module'
    assert sys.modules['utils.track_catalog'].__class__.__name__ == 'module'
    assert sys.modules['backends.dfplayer_backend'].__class__.__name__ == 'module'
