# Changes Log (v2)

This document retroactively records the additions and updates introduced in the v2 pass to support the Waveshare 1.44" ST7735 button variant and the documentation improvements.

## 2025-11-12 — Variant + Docs + Tests

Added
- `WAVESHARE_144_MIGRATION_PLAN_v2.md`
  - Revised migration plan with SPI/luma install details, clarified entrypoint/service usage, PRESS/HOLD policy, detection guidance, reconciled estimates, optional enhancements.
- `src/hardware/display_st7735.py`
  - New display abstraction with emulator fallback and backlight PWM hooks. Mockable seams; no hard dependency on luma.lcd for tests.
- `src/hardware/button_input.py`
  - New GPIO input abstraction with PRESS/HOLD/RELEASE, debounce, poll/interrupt backends, and injected GPIO seam.
- `src/backends/dfplayer_backend_v2.py`
  - v2 backend using absolute hardware import to avoid parent-relative import issues.
- `src/utils/track_catalog_v2.py`
  - v2 track catalog loader using absolute import (`from core.state import Track`).
- `src/utils/calibration_v2.py`
  - v2 touch calibration using absolute imports for hardware modules.
- `src/core/profile_select_v2.py`
  - Profile detection and selection returning dotted paths for testability.
- `src/main_v2.py`
  - v2 entrypoint with profile selection and minimal 128×128 UI path for `st7735_buttons`.
- `scripts/install_st7735_buttons_v2.sh`
  - Variant installer: enables SPI, installs `python3-spidev`, `python3-rpi.gpio`, luma.lcd (apt/pip), ensures group membership, installs fonts.
- `systemd/dfplayer-144lcd.service`
  - Variant service: `WorkingDirectory=/home/pi/pi-tft-dfplayer`, environment `DFPLAYER_HW_PROFILE=st7735_buttons`, `ExecStart=/usr/bin/python3 src/main.py`.
- `docs/st7735_setup.md`, `docs/button_reference.md`
  - Setup instructions and button mapping/reference for the variant.
- `tests/hardware/test_display_st7735.py`, `tests/hardware/test_button_input.py`
  - Unit tests using emulator and fake GPIO to validate added modules without hardware.
- `tests/core/test_profile_select_v2.py`
  - Verifies profile selection returns expected dotted classes.
- `src/main_touch_v2.py`
  - Touchscreen launcher that aliases original modules to v2 counterparts, preserving the existing UI while fixing import issues without modifying original files.
- `tests/main/test_main_touch_v2.py`
  - Ensures bootstrap installs lazy module proxies for v2 modules.
- `systemd/dfplayer-fb-v2.service`
  - Touchscreen v2 systemd unit that runs `src/main_touch_v2.py`.
- `docs/touch_v2_setup.md`
  - Touchscreen v2 setup and troubleshooting guide.
- `docs/smoke_test_checklist_v2.md`
  - Combined smoke test checklist for touchscreen v2 and 1.44" variant.
  
Updated
- `docs/touch_v2_setup.md`
  - Added Hardware Override section with CLI/env examples for explicit touchscreen selection when using `main_v2.py`.
- `docs/st7735_setup.md`
  - Added Hardware Override section with CLI/env examples and emulator usage.
- `VERSIONING_GUIDELINES.md`
  - Repository convention for file-based versioning and documentation requirements.
- `src/ui/draw_utils_v2.py`
  - Pure geometry and text-wrapping helpers for UI code; tested without PIL.
- `src/ui/views_v2.py`
  - Small reusable view helpers for the 128×128 layout (play indicator, track number, artwork panel, title line, volume bar).
- Refactor: `src/main_v2.py` now composes its 128×128 rendering using `views_v2` helpers for cleaner structure.
- `tests/ui/test_draw_utils_v2.py`
  - Validates geometry utilities and greedy word-wrapping behavior.
- `README.md`
  - Added v2 hardware profiles section, profile selection instructions, emulator notes, and links to setup/smoke-test docs.
  - Updated with v3 auto-detection precedence (CLI > env > config > auto).
- `src/core/profile_select_v3.py`
  - New v3 selector with auto-detection (fb/hat) and override precedence.
- `tests/core/test_profile_select_v3.py`
  - Tests for env/config overrides and auto-detect paths.

Notes
- Existing modules were not modified in-place for this pass; new functionality is additive to avoid regressions.
- Startup import regressions unrelated to this variant were documented in `codex_review.md`. Those should be addressed by reverting parent-relative imports or moving to a true package (see recommendations inside that file).

Validation
- Imported new modules directly to ensure import succeeds without hardware.
- New tests can be executed (with pytest installed) using:
  ```bash
  pytest -q tests/hardware/test_display_st7735.py tests/hardware/test_button_input.py
  ```
- Emulator mode for display can be forced via `DFPLAYER_USE_EMULATOR=1`.
