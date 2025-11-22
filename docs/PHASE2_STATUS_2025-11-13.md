# Phase 2 Status — 2025-11-13 (Legacy)
Legacy phase status. Log new status in `docs/ai/TASK_LOG.md`; current direction in `docs/ai/PROJECT_GUIDE.md`.

This checkpoint summarizes the current state of the Phase 2 migration (ScreenManagerV2 + Application/AppState) so the next developer can pick up without re-reading every file.

## Architecture Grade (B-)
- **Strengths**: clear separation between front-end (`ui/framework_v2`, `ui/screens_v2`) and services (`backends/dfplayer_backend.py`, `core/state_v2.py`); ScreenManagerV2 already powers Home, Track Browser, and Now Playing screens; DFPlayer backend now surfaces events asynchronously.
- **Weaknesses**: entrypoints are fragmented (`main.py`, `main_v2.py`, `main_v3.py`), and only the button variant uses the new state abstractions; `app_v2.Application` still touches framebuffer/evdev directly with no dependency injection, making it hard to test or reuse for other profiles; the migration branch lacks a unified event loop so DFPlayer events stall when touch input is idle.

## Key Observations
- `src/main_v2.py` now targets the 1.44" button profile, but it previously attempted to import a non-existent `dfplayer_backend_v2`. The variant now uses `backends.dfplayer_v2.DFPlayerBackend` and tracks the active hardware profile so rendering decisions are explicit.
- `src/ui/views_v2.py` referenced `src.ui.*`, which broke when modules were imported as `ui.*`. Imports are now relative/absolute in the expected namespaces so tests and scripts agree on the same package path.
- `src/main_v3.py` successfully boots the new `Application`, but the application itself still owns low-level hardware resources. The next refactor should wrap framebuffer/touch handling in services so both `main_v2.py` and `main_v3.py` can share the same event loop.
- `DFPLAYER_UI_FRAMEWORK=1` now executes the `Application` class directly from `src/main.py`, so the touchscreen path exercises the same ScreenManagerV2 pipeline as `main_v3.py` without needing the legacy adapter.
- Gesture handling is live: the Application emits `drag`/`drag_end` events with previous touch points, the Track Browser honors drag scrolling with bounds/hitboxes, and slider drags persist volume through Config, so the v2 UI now feels closer to the legacy experience.
- README and `VERSIONING_GUIDELINES.md` now explain how we will transition away from `_vN` files into Git branches once `main_v3` is stable.

## Immediate To-Do List
1. Wire `Application` (AppState + ScreenManagerV2) into the touchscreen path so we have a single event loop for both hardware profiles.
2. Implement the seven outstanding migration items listed in `docs/PHASE_2_IMPLEMENTATION_SUMMARY.md` (autoplay in the new stack, real widgets, non-blocking rendering, etc.).
3. Add unit tests for `app_v2.Application` hooks (mock framebuffer/touch) so regressions surface before hardware testing. See `tests/README.md` for the legacy test harness and `tests/README_v2.md` for the new suite layout.
4. Update the systemd units to point at the new entrypoint once the migration branch is merged; keep the legacy units in `legacy/v1` for recovery.

## Validation Status
- `pytest -q tests/ui/test_widgets_v2.py tests/ui/test_draw_utils_v2.py tests/core/test_profile_select_v3.py tests/core/test_profile_select_v2.py tests/hardware/test_display_st7735.py tests/hardware/test_button_input.py tests/main/test_main_touch_v2.py tests/ui/test_views_v2.py`
- Run `./scripts/smoke_test_v2.sh` before touching real hardware, then document manual validation steps in `docs/smoke_test_checklist_v2.md`.

Track follow-up work in `CHANGES_v2.md` and link commits so each iteration can be compared quickly.
