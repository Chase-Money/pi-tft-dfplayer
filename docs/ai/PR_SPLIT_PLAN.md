# PR Split Plan (keep PRs small)

Context: framework-migration grew large. Split remaining work into focused PRs:

1) Core consolidation (PR1)
   - Runtime imports use ConfigV2/AppState; legacy config paths marked legacy.
   - Canonical entrypoint: `src/main.py` + `app_v2` + `ui/framework` + `ui/screens`.
   - Mark `main_tft_v2.py` as legacy; no new code paths depend on it.
   - Keep `dfplayer_fb_gui.py` only as a test stub (not runtime).
   - Ensure tests green.

2) UI migration + theming (PR2)
   - Move remaining legacy UI logic (artwork/progress/controls) into v2 screens.
   - Apply theme palette across all screens (settings/calibration/etc.); pass palette via renderer context (no hardcoded colors).

3) Cleanup (PR3)
   - Remove/ archive legacy runtime modules (main_tft_v2, old frameworks/screens), keep test stub if required.
   - Update docs/README to point only to `src/main.py` for runtime; note legacy modules are for tests.

Current state: entrypoint is `src/main.py`; ConfigV2 is canonical in app_v2; legacy monolith stub retained for tests; tests passing.
