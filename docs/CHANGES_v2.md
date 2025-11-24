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
- `src/ui/app_v2.py`
  - TouchscreenFrameworkApp bridge between DFPlayerApp state and the new screen manager.
- `src/ui/framework_v2/*`
  - Added screen manager, UI events, and widget primitives used by the Phase 2 UI.
- `src/ui/screens_v2/*`
  - Placeholder Home, Track Browser, and Now Playing screens built on the new framework.
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
  - Documented the experimental `DFPLAYER_UI_FRAMEWORK=1` flag and expanded the Tests section for the new workflow.
- `src/core/profile_select_v3.py`
  - New v3 selector with auto-detection (fb/hat) and override precedence.
- `tests/core/test_profile_select_v3.py`
  - Tests for env/config overrides and auto-detect paths.
- `docs/PHASE_2_IMPLEMENTATION_SUMMARY.md`
  - Added follow-up recommendations (auto-advance processing, serial locking, reset integration) for the Phase 2 DFPlayer enhancements based on review feedback.
- `requirements.txt`
  - Consolidated runtime Python dependencies (Pillow, pyserial, evdev) for the classic `pip install -r requirements.txt` workflow.
- `src/hardware/touch.py`
  - Added backward-compatible defaults to `scale_xy` so legacy callers continue to work without passing the new arguments.
- `src/dfplayer_fb_gui.py`
  - Introduced `_dfplayer_checksum`, restored serial timeouts via `finally`, clarified `send()` parameter docs, and standardized auto-generated track labels to three digits.
- `src/main.py`, `src/ui/screen.py`
  - Display track numbers using three digits to match catalog formatting.
- `src/hardware/dfplayer.py`
  - Added checksum helper and a `read_response` API so callers can consume DFPlayer notifications.
- `src/backends/dfplayer_backend.py`
  - Added a background listener thread and event queue (`poll_event`) to surface DFPlayer events (track finished/started, errors).
- `src/main.py`
  - Drains backend `poll_event()` results from the main loop, auto-advancing tracks and keeping the UI responsive even when no touch input occurs. Touch handling now uses `select` instead of blocking on `read_loop()`, laying the groundwork for the full event-loop refactor.
- `src/ui/framework_v2/widgets.py`, `src/ui/screens_v2/track_browser.py`
  - ListWidget now supports dynamic item/row updates and tap hit-testing; the Track Browser screen renders real track data, syncs scroll offsets with application state, and plays tracks on tap within the ScreenManager UI.
- `src/ui/screens_v2/now_playing.py`
  - ScreenManager-based Now Playing view now toggles backend playback via the Play/Pause button and updates volume (state + backend) when tapping the slider.

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

## 2025-11-13 — Entry point cleanup, documentation, and UI tests

Added
- `docs/PHASE2_STATUS_2025-11-13.md`
  - Architecture grade (B-), key observations on `main_v2.py`/`main_v3.py`, and a concrete to-do list for the next developer.
- `tests/ui/test_views_v2.py`
  - Verifies the `views_v2` helpers render without overruns and keeps imports honest across both `ui.*` and `src.ui.*` usage.
- `tests/core/test_state_v2.py`
  - Exercises the new AppState helpers (`set_tracks`, `set_metadata`, `get_index_by_number`) to guard against regressions as the ScreenManager gains features.
- `tests/ui/test_widgets_v2.py`
  - New coverage for `ListWidget.scroll_pixels` to ensure drag-based scrolling stays within bounds.

Updated
- `.gitignore`
  - Now ignores agent-generated collaboration files (`AGENTS.md`, `CLAUDE*.md`, `GEMINI*.md`, etc.) so future commits stay clean.
- `README.md`
  - Added a "How to Proceed on Your Device" section covering both hardware profiles and documented how to boot the new `src/main_v3.py` Application path.
  - Captured the plan for transitioning away from `_vN` files into pure Git branching once the migration branch stabilizes.
- `VERSIONING_GUIDELINES.md`
  - Documented the concrete steps for the eventual `_vN` → Git-only cutover (freeze promoted files, archive legacy branch, document tags/commits).
- `docs/PHASE_2_IMPLEMENTATION_SUMMARY.md`
  - Logged the seven outstanding migration items surfaced during hardware smoke tests so they can be tracked explicitly.
- `src/main_v2.py`
  - Uses the correct DFPlayer backend module, records the selected hardware profile, and bases rendering decisions on that profile instead of brittle class-name checks.
- `src/ui/views_v2.py`
  - Switched to relative imports so the module behaves the same whether it is imported via `ui.views_v2` (tests) or `src.ui.views_v2` (Application).
- `src/core/state_v2.py`
  - Added metadata helpers and track setters so the ScreenManager can synchronize real catalog/metadata data and respond to DFPlayer events via track numbers.
- `src/ui/screens_v2/now_playing.py`
  - Volume adjustments now persist to Config when the slider is dragged, keeping behavior consistent with the legacy UI.
- `src/app_v2.py`
  - Rewritten to initialize actual hardware (Framebuffer + TouchInput), load the real track catalog/metadata, wire up the DFPlayer backend, and translate touch/drag gestures into ScreenManagerV2 events. Backend events (track finished/started) now drive AppState directly for autoplay.
- `src/main.py`
  - When `DFPLAYER_UI_FRAMEWORK=1` is set, the entrypoint now executes `src/app_v2.Application` instead of the legacy adapter so both hardware profiles share the new event loop.
- `src/ui/framework_v2/widgets.py`, `src/ui/screens_v2/track_browser.py`
  - ListWidget gained pixel-wise scrolling (with fractional accumulation) and the Track Browser now consumes drag/drag_end events to provide smooth list scrolling with state-backed hitboxes.
- `src/app_v2.py`
  - Touch handling now differentiates taps vs drags, dispatches `drag_end` events, and includes previous points in drag payloads so widgets can implement inertial scrolling or sliders without hacks.
- `README.md`, `docs/PHASE_2_IMPLEMENTATION_SUMMARY.md`, `docs/PHASE2_STATUS_2025-11-13.md`
  - Documented the new entrypoint flow and noted that the ScreenManager integration is now live for the touchscreen profile.
- `README.md`
  - Reorganized the opening sections with proper headings, bullet lists, and fenced code blocks so hardware requirements, wiring, software snapshot, and quick-start instructions are easier to scan.
- `.gitignore`, `README.md`
  - Added a dedicated `.agent-notes/` scratch directory (ignored by git) and documented how to use it so CLI/LLM context files stay local while curated docs remain tracked.
- `src/ui/screens_v2/calibration.py`, `src/ui/screens_v2/settings.py`
  - New calibration workflow (four-point tap targets, raw driver inversion, config persistence) and a settings hub for orientation cycling + calibration entry.
- `src/ui/screens_v2/home.py`, `src/ui/screens_v2/track_browser.py`, `src/ui/screens_v2/now_playing.py`
  - Added status-banner overlays, button feedback, slider smoothing, track list drag scrolling, artwork placeholders, and quick access to settings.
- `src/ui/framework_v2/widgets.py`
  - Button flash feedback, slider easing, and list pixel-scroll helpers to make the v2 UI feel responsive.
- `src/main_tft_v2.py`, `src/hardware/touch_controller.py`
  - Touch events now carry raw coordinates, configuration-driven orientation/calibration is respected, status messaging is exposed to screens, and new screens are registered with the manager.
- `README.md`
  - Documented the Settings/Calibration flow under the Phase 2 pilot instructions.
  - Added guidance for freeing `/dev/fb1` from the desktop via `scripts/disable_desktop_and_free_fb1.sh` (tft-only, hdmi, restore options).
- `requirements.txt`, `scripts/install_prereqs.sh`
  - Added NumPy dependency for the accelerated framebuffer conversion path and ensured apt installs `python3-numpy` on-device.

Validation
- `pytest -q tests/ui/test_draw_utils_v2.py tests/ui/test_widgets_v2.py tests/ui/test_views_v2.py tests/core/test_profile_select_v3.py tests/core/test_profile_select_v2.py tests/hardware/test_display_st7735.py tests/hardware/test_button_input.py tests/main/test_main_touch_v2.py`
- `pytest -q tests/core/test_state_v2.py`

## 2025-11-20 — V2 Display Fix & Touch Debugging

Fixed
- **src/main_tft_v2.py** - Corrected framebuffer device defaults from `/dev/fb0` (HDMI) to `/dev/fb1` (TFT)
  - Line 55: Class constructor `fb_device` parameter default
  - Line 611: argparse `--fb` argument default
  - Line 156: Added diagnostic logging for framebuffer device path verification
- **src/ui/screens_v2/home.py** - Removed debug red rectangle artifacts that were visible on screen
- **/boot/firmware/cmdline.txt** - Fixed console mapping (`fbcon=map:1` → `fbcon=map:01`) to free fb1 from Linux console

Status
- ✅ V2 app now displays correctly on 3.5" TFT screen at ~4.8 FPS
- ✅ HomeScreen UI with three buttons renders properly
- ⚠️ Touch input not yet responding (buttons display but don't react to touches)
- ⚠️ Performance at 4.8 FPS vs. expected 15-16 FPS (needs profiling)

Documentation
- **TFT_DEBUG_LOG.md** - Added detailed debugging notes for next developer including:
  - Root cause analysis of framebuffer device mismatch
  - Touch input debugging strategy
  - Performance investigation steps
  - Testing commands and verification procedures

Known Issues
- Touch events are being generated by hardware but not routing to button widgets
- Needs investigation in `_process_touch_events()` event routing pipeline
- Widget hit detection may need coordinate alignment verification
