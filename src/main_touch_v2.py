#!/usr/bin/env python3
"""Touchscreen entrypoint (v2) that keeps the original UI but fixes imports."""

import importlib
import os
import sys
from types import ModuleType


def _lazy_proxy(target_module: str) -> ModuleType:
    """Create a module proxy that lazily imports `target_module` on demand."""
    mod = ModuleType(target_module)

    def __getattr__(name: str):  # type: ignore
        real = importlib.import_module(target_module)
        return getattr(real, name)

    mod.__getattr__ = __getattr__  # type: ignore[attr-defined]
    return mod


def bootstrap_aliases() -> dict:
    mapping = {}

    src_dir = os.path.dirname(__file__)
    if src_dir and src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    cal_proxy = _lazy_proxy('src.utils.calibration')
    cat_proxy = _lazy_proxy('src.utils.track_catalog')
    be_proxy = _lazy_proxy('src.backends.dfplayer_v2')

    sys.modules['utils.calibration'] = cal_proxy
    sys.modules['utils.track_catalog'] = cat_proxy
    sys.modules['backends.dfplayer_backend'] = be_proxy

    mapping['utils.calibration'] = cal_proxy
    mapping['utils.track_catalog'] = cat_proxy
    mapping['backends.dfplayer_backend'] = be_proxy

    return mapping


def main():  # pragma: no cover - integration launcher
    bootstrap_aliases()
    main_mod = importlib.import_module('main')
    return main_mod.main()


if __name__ == '__main__':  # pragma: no cover - manual execution path
    main()

