# Project Guide (Source of Truth)

Single reference for agents and devs. Always read this and `CODING_STANDARDS.md` before working.

## Current Architecture Direction
- Unify on the v2 framework: ScreenManagerV2 + FramebufferRendererV2 + AppState/Config v2.
- No new `_v2` file forks; all changes go into the unified modules under `src/`.
- Entry point: `src/main.py` (uses app_v2 + ConfigV2 + TouchController + ScreenManagerV2).
- Hardware boundaries: keep framebuffer, touch, DFPlayer in `src/hardware/` and `src/backends/`, UI in `src/ui/`.

## Refactoring Plan (snapshot)
- Phase 1: merge config/state into single sources; establish main entrypoint.
- Phase 2: finalize renderer/framework locations under `src/ui/`.
- Phase 3: migrate monolith `dfplayer_fb_gui.py` logic into screens/components; wire touch/events/backends.
- Phase 4: delete superseded `_v2`/legacy files, update README/docs, keep tests green.

## Refactoring Status - COMPLETE ✅

**Framework Migration Complete** - All refactoring tasks have been successfully completed as of December 2025.

### ✅ Completed Tasks

1.  **Consolidate Versioned Files:**
    *   ✅ Removed legacy files: `src/dfplayer_fb_gui.py`, `src/core/profile_select_v2.py`, `src/core/state_v2.py`
    *   ✅ Archived `src/ui/screen.py` and components to `archive/` (already done)
    *   ✅ Renamed adopted files:
        *   `src/core/config_v2.py` → `src/core/config.py`
        *   `src/core/profile_select_v3.py` → `src/core/hardware_profile.py`
        *   `src/app_v2.py` → `src/app.py`
        *   `src/backends/dfplayer_v2.py` → `src/backends/dfplayer.py`

2.  **Refactor DFPlayer Backend:**
    *   ✅ Eliminated duplication - uses `src/hardware/dfplayer.DFPlayer` for low-level communication
    *   ✅ Implements `src/backends/base.PlaybackBackend` interface
    *   ✅ Added `poll_event()` method for asynchronous status processing
    *   ✅ Added `poll_event` to base interface

3.  **Consolidate Font Loading:**
    *   ✅ All font management handled by `src/ui/renderer.py`
    *   ✅ Screens receive fonts from renderer context
    *   ✅ Eliminated overlapping logic in app.py

### ✅ Additional Improvements
- **Documentation Consolidation:** Reduced 40+ files to 5 comprehensive documents
- **Code Quality:** Achieved 85/100 score (B grade)
- **Test Coverage:** 188/188 tests passing
- **Architecture:** Clean separation of hardware/backends/core/ui layers
- **Thread Safety:** Proper synchronization and resource management

## Documentation Layout
- **Source of truth:** this file + `CODING_STANDARDS.md` (and optional `TASK_LOG.md`) under `docs/ai/`.
- **Legacy/Reference:** older debug logs and reports live under `docs/` (e.g., `TFT_DEBUG_LOG.md`, `DEBUG_SESSION_REPORT.md`, `TOUCH_DEBUG_CHANGES.md`, `TOUCH_INPUT_DEBUG.md`). Prefer adding new entries to `docs/ai/TASK_LOG.md` and keep legacy files untouched unless summarizing.

## Workflow & Git
- Use feature branches for all work (e.g., `feature/theme-engine-lcars`).
- Keep `main` stable; no unchecked `_v2` copies.
- Document non-obvious behavior or hardware expectations in `docs/` or `docs/ai/` as appropriate.
- Before planning/starting work, read `docs/ai/TASK_LOG.md` to pick up where the team left off and append your updates when done.

## Touch & DFPlayer Notes
- Touch: ensure calibration/orientation from config, sane gesture thresholds (tap ~400ms, drag ~12px, swipe ~48px); process full event batches.
- DFPlayer: guard UART open failures, keep commands idempotent, log warnings not crashes.

## Theming
- Themes live in `themes/*.json`; select via `DFPLAYER_THEME`. Schema and samples: see `docs/LCARS_THEME_PLAN.md`.

## Future Development Roadmap

For planning of major new features and significant improvements, refer to the following document:

- **[Reliability, Performance, and Spotify Integration Plan](../reliability_spotify.md)**: Details strategies for improving UI rendering performance, making hardware communication more robust, and provides a step-by-step guide for integrating Spotify as a new audio backend.
