#!/usr/bin/env python3
"""
Touchscreen entrypoint (v2) that keeps the original UI but fixes imports.

This launcher aliases the original modules to their v2 counterparts to avoid
the parent-relative import regressions, then imports and runs `main.main()`.
It does not modify existing files, preserving the v2 versioning rule.

Run: `python3 src/main_touch_v2.py`
Service: can be wired similarly to dfplayer-fb if desired.
"""

import importlib
import sys
from types import ModuleType


def _lazy_proxy(target_module: str) -> ModuleType:
    """Create a module proxy that lazily imports `target_module` on attribute access."""
    mod = ModuleType(target_module)

    def __getattr__(name: str):  # type: ignore
        real = importlib.import_module(target_module)
        return getattr(real, name)

    mod.__getattr__ = __getattr__  # type: ignore[attr-defined]
    return mod


def bootstrap_aliases() -> dict:
    """Install v2 module aliases for the original module names.

    Returns a mapping of original->v2 module objects to aid testing.
    """
    mapping = {}

    # Ensure src/ directory is on sys.path for absolute imports in main.py
    # Running as a script from src/ provides this, but keep it explicit.
    if sys.path[0] == '' or not sys.path[0].endswith('/src'):
        # Try to derive src directory from this file path
        import os
        src_dir = os.path.dirname(__file__)
        if src_dir and src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    # Create lazy alias modules under original names
    cal_proxy = _lazy_proxy('src.utils.calibration_v2')
    cat_proxy = _lazy_proxy('src.utils.track_catalog_v2')
    be_proxy = _lazy_proxy('src.backends.dfplayer_backend_v2')

    sys.modules['utils.calibration'] = cal_proxy
    sys.modules['utils.track_catalog'] = cat_proxy
    sys.modules['backends.dfplayer_backend'] = be_proxy

    mapping['utils.calibration'] = cal_proxy
    mapping['utils.track_catalog'] = cat_proxy
    mapping['backends.dfplayer_backend'] = be_proxy

    return mapping


def main():  # pragma: no cover - integration launcher
    bootstrap_aliases()
    # Import and run the original touchscreen app
    main_mod = importlib.import_module('main')
    return main_mod.main()


if __name__ == '__main__':  # pragma: no cover - manual execution path
    main()
