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

## Current Refactoring Tasks

Based on the latest codebase review, here are the immediate refactoring priorities:

1.  **Consolidate Versioned Files:**
    *   Remove legacy files: `src/dfplayer_fb_gui.py` and `src/core/config.py`.
    *   Archive `src/ui/screen.py` (and any components exclusively used by it) to `archive/` as it's superseded.
    *   Rename adopted `_v2`/`_v3` files:
        *   `src/core/config_v2.py` -> `src/core/config.py`
        *   `src/core/profile_select_v3.py` -> `src/core/hardware_profile.py`

2.  **Refactor DFPlayer Backend (`src/backends/dfplayer_v2.py`):**
    *   **Eliminate Duplication:** Modify `src/backends/dfplayer_v2.py` to *use an instance of* `src/hardware/dfplayer.DFPlayer` for all low-level serial communication, instead of duplicating its logic (`_checksum`, `_send_command`, `read_response`).
    *   **Implement Interface:** Make `src/backends/dfplayer_v2.py` inherit from `src/backends/base.PlaybackBackend` and implement all its abstract methods.
    *   **Add Event Polling:** Implement a `poll_event()` method in `src/backends/dfplayer_v2.py` to process incoming asynchronous DFPlayer status messages, as expected by `src/app_v2.py`. (Also, add `poll_event` to `src/backends/base.py`'s `PlaybackBackend` abstract interface).

3.  **Consolidate Font Loading:**
    *   Ensure all font loading and management is handled exclusively by `src/ui/renderer.py`. The `ScreenManagerV2` and individual screens should consistently receive fonts from the renderer's context, eliminating any overlapping logic in `src/app_v2.py`.

## Documentation Layout
- **Source of truth:** this file + `CODING_STANDARDS.md` (and optional `TASK_LOG.md`) under `docs/ai/`.
- **Legacy/Reference:** older debug logs and reports live under `docs/` (e.g., `TFT_DEBUG_LOG.md`, `DEBUG_SESSION_REPORT.md`, `TOUCH_DEBUG_CHANGES.md`, `TOUCH_INPUT_DEBUG.md`). Prefer adding new entries to `docs/ai/TASK_LOG.md` and keep legacy files untouched unless summarizing.

## Workflow & Git
- Use feature branches for all work (e.g., `feature/theme-engine-lcars`).
- Keep `main` stable; no unchecked `_v2` copies.
- Document non-obvious behavior or hardware expectations in `docs/` or `docs/ai/` as appropriate.

## Touch & DFPlayer Notes
- Touch: ensure calibration/orientation from config, sane gesture thresholds (tap ~400ms, drag ~12px, swipe ~48px); process full event batches.
- DFPlayer: guard UART open failures, keep commands idempotent, log warnings not crashes.

## Theming
- Themes live in `themes/*.json`; select via `DFPLAYER_THEME`. Schema and samples: see `docs/LCARS_THEME_PLAN.md`.
