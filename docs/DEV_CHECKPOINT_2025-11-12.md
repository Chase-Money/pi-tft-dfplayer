# Developer Checkpoint — 2025-11-12

This checkpoint captures the current state after introducing v2/v3 foundations, so other developers can pick up smoothly.

## What’s Landed (v2/v3)

- Hardware variant split
  - Touchscreen v2 launcher: `src/main_touch_v2.py` + `systemd/dfplayer-fb-v2.service`
  - 1.44" ST7735 variant: `src/main_v2.py` + `systemd/dfplayer-144lcd.service`
- Profile selection
  - v3 selector with override precedence + auto-detect: `src/core/profile_select_v3.py`
  - Fallback to v2 selector if v3 unavailable
- Hardware abstractions (button variant)
  - Display: `src/hardware/display_st7735.py` (emulator + backlight PWM hooks)
  - Input: `src/hardware/button_input.py` (PRESS/HOLD/RELEASE, debounce)
- UI (button variant)
  - Minimal now-playing for 128×128 in `src/main_v2.py`
  - View helpers: `src/ui/views_v2.py`
  - Pure helpers: `src/ui/draw_utils_v2.py`
- Touchscreen compatibility
  - v2 modules fix import regressions: `src/utils/*_v2.py`, `src/backends/dfplayer_backend_v2.py`
  - `main_touch_v2.py` installs lazy aliases to v2 modules, then runs the original `src/main.py`
- Docs & Scripts
  - Setup: `docs/touch_v2_setup.md`, `docs/st7735_setup.md`
  - Smoke tests: `docs/smoke_test_checklist_v2.md`, `scripts/smoke_test_v2.sh`
  - Versioning & changes: `VERSIONING_GUIDELINES.md`, `CHANGES_v2.md`
  - README updated with v2/v3 usage

## Tests

- Added and passing (run with pytest):
  - `tests/hardware/test_display_st7735.py` — emulator path
  - `tests/hardware/test_button_input.py` — fake GPIO
  - `tests/core/test_profile_select_v2.py`, `tests/core/test_profile_select_v3.py`
  - `tests/main/test_main_touch_v2.py` — lazy alias bootstrap
  - `tests/ui/test_draw_utils_v2.py` — geometry/wrapping helpers
- Run locally:
  ```bash
  pytest -q tests/ui/test_draw_utils_v2.py \
          tests/core/test_profile_select_v3.py tests/core/test_profile_select_v2.py \
          tests/hardware/test_display_st7735.py tests/hardware/test_button_input.py \
          tests/main/test_main_touch_v2.py
  ```

## Known Gaps / To‑Do (handoff)

- Legacy v1 modules still contain parent‑relative imports; use `main_touch_v2.py` to avoid issues. Do not import v1 modules directly in new code.
- `src/main_v2.py` currently implements a minimal 128×128 UI; future work:
  - Add TRACK_LIST / VOLUME / INFO screens using `views_v2.py`
  - Input routing per screen and alphabet jump behavior
  - Optional backlight PWM fades
- Add unit tests for `core/config.py`, `core/state.py`, `core/events.py` (see TEST_PLAN.md priorities)
- Decide on packaging (pyproject + console_scripts) and simple CI for tests

## Alignment with Other Dev Docs

- CODE_REVIEW_SUMMARY.md — many critical issues highlighted for the monolith are addressed by v2 modules and new patterns (resource cleanup, path traversal in metadata, error handling). Legacy `dfplayer_fb_gui.py` should be considered frozen/legacy; prefer v2 paths.
- IMPLEMENTATION_ROADMAP.md — Spotify/Bluetooth/multi‑screen are future phases. Current work maps to Phase 1 (core refactor) and early UI modularization.
- PROJECT_STATUS.md — Some claims (coverage, readiness) seem optimistic relative to this repo state. Use v2/v3 foundations as the new baseline for quality bars.

## Quick Start (Both Profiles)

- Touchscreen v2
  ```bash
  ./scripts/install_prereqs.sh
  ./scripts/apply_system_tweaks.sh
  sudo reboot
  sudo cp systemd/dfplayer-fb-v2.service /etc/systemd/system/
  sudo systemctl enable --now dfplayer-fb-v2
  ```
- 1.44" ST7735 buttons
  ```bash
  ./scripts/install_st7735_buttons_v2.sh
  sudo reboot
  sudo cp systemd/dfplayer-144lcd.service /etc/systemd/system/
  sudo systemctl enable --now dfplayer-144lcd
  ```

## Contact Points / Notes

- Prefer `src/main_v2.py` and `src/main_touch_v2.py` for all new work.
- Keep v2 file/versioning convention and update `CHANGES_v2.md` with any changes.
- When adding UI, extend `src/ui/views_v2.py` and keep helpers pure where possible.
- The Phase 2 screen-manager harness is live behind `DFPLAYER_UI_FRAMEWORK=1` in `src/main.py`. Run `pip install -e .` + `python -m pytest` to use the new tests, and wire additional screens via `ui/framework_v2`.
- DFPlayer autoplay is now handled asynchronously: `backends/dfplayer_backend` exposes `poll_event()`, and `DFPlayerApp` runs a worker thread that advances tracks on `track_finished` events. No touch interaction is needed for auto-advance. Thread startup/cleanup logic lives in `DFPlayerApp`.
