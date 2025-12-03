# Test Suite (v2) — Modular Paths and Variants

This document describes the v2 test suite that validates the new modular code paths (profile selection, hardware abstractions for the 1.44" variant, and UI helpers). It complements, but does not replace, the legacy tests for `dfplayer_fb_gui.py` documented in `tests/README.md`.

## What These Tests Cover

- Profile selection (v2/v3): precedence and auto-detect
- ST7735 display abstraction (emulator path; no hardware required)
- GPIO button input abstraction (fake GPIO; no hardware required)
- Touchscreen v2 bootstrap (lazy aliasing for legacy imports)
- Pure UI helpers (geometry, greedy wrapping)

## Test Layout

```
tests/
├── core/
│   ├── test_profile_select_v2.py        # v2 profile selection
│   └── test_hardware_profile.py         # v3 with auto-detect
├── hardware/
│   ├── test_display_st7735.py           # emulator-based tests
│   └── test_button_input.py             # fake GPIO tests
├── main/
│   └── test_main_touch_v2.py            # lazy alias bootstrap
└── ui/
    ├── test_draw_utils_v2.py            # pure helpers
    ├── test_screen_manager_v2.py        # navigation + event routing
    └── test_widgets_v2.py               # button/list/slider behaviors
```

## Running v2 Tests

Install dependencies (once):
```bash
pip install -e .
pip install pytest
```

Run the v2 tests:
```bash
pytest -q tests/ui/test_draw_utils_v2.py \
        tests/core/test_hardware_profile.py tests/core/test_profile_select_v2.py \
        tests/hardware/test_display_st7735.py tests/hardware/test_button_input.py \
        tests/main/test_main_touch_v2.py
```

## Notes

- These tests are designed to run without hardware by using an emulator (`DisplayST7735`) and a fake GPIO shim.
- The touchscreen v2 launcher (`main_touch_v2.py`) avoids importing heavy dependencies at import time via lazy module proxies; the test validates the proxy installation.
- For on-device validation of the full stacks, see `docs/smoke_test_checklist_v2.md` and use the provided systemd units.

## Legacy Tests

- The legacy test suite for `dfplayer_fb_gui.py` remains in `tests/` and is documented in `tests/README.md`. It focuses on static analysis and TDD fixes for the monolithic file and may require hardware packages (evdev) to pass fully on non-Pi systems.
