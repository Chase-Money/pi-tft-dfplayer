# Task Log (optional)

- Use this to note significant tasks, branches, test runs, and hardware validation steps.
- Format suggestion: `YYYY-MM-DD | branch | task | tests | notes`
- Legacy logs remain in `docs/` with "(Legacy)" headers; add new items here.

2025-11-20 | feature/theme-engine-lcars | Integrated theme loader, palette constants into dfplayer_fb_gui; added LCARS/HA/RPi theme samples | Tests not run (manual) | Theming groundwork complete.
2025-11-21 | feature/theme-engine-lcars | Fixed touch event batching, tightened gesture thresholds, reduced touch logging; marked debug docs as legacy | venv/bin/pytest -q (pass) | Touch pipeline more responsive; 188 tests green.
2025-11-22 | feature/framework-migration | Phase 2 complete: Consolidated UI framework (_v2 → canonical); Added HEAVY OPERATOR guidelines | 188/188 tests pass | Framework migration successful.
2025-11-22 | feature/framework-migration | Phase 3 complete: Created ArtworkWidget, archived monolithic code (1,995 lines), updated systemd service to main.py | 166/166 tests pass | Migration complete, ready for hardware testing.
2025-11-23 | feature/framework-migration | Fixed all PR #15 test failures: touch batching, SWAP_XY transform, threading.Lock isinstance | 188/188 tests pass (CI ✅) | PR #15 ready for merge.
2025-11-24 | feature/framework-migration | Captured PR split plan (PR_SPLIT_PLAN.md): PR1 core consolidation, PR2 UI + theme migration, PR3 cleanup | n/a | Keep PRs small per bot feedback.
2025-11-24 | feature/framework-migration | Touch hardening (thresholds, debounce, hitbox expansion); legacy test stubs restored; optional tap/hitbox debug logging flag added | pytest -q (subset; full run pending) | Start hardware validation for tap accuracy/back button.
2025-11-24 | feature/framework-migration | Added partial push plumbing (push_partial) and initial dirty-rect plumbing in renderer/screens | pytest -q (quick) pending | Next: refine dirty rect collection & full test run.
2025-11-26 | feature/framework-migration | PR #17: Framework migration consolidation - config merge, DFPlayer refactoring, file cleanup, snake_case standardization | 188/188 tests pass (CI ✅) | Ready for merge after bot review fixes.
2025-11-26 | feature/framework-migration | Bot review fixes: calibration validation, state sync in DFPlayer, thread timeout increase, event queue monitoring | CI tests pass | Addressed all "Must Fix" and "Should Fix" items from bot review.
2025-11-24 | feature/framework-migration | Added RobustSerial wrapper and hooked into DFPlayerBackend (initial wiring) | pytest -q (quick) pending | Needs hardware validation and potential DFPlayer integration adjustments.
2025-11-27 | feature/framework-migration | Fixed framebuffer partial write bug; standardized DFPlayer error handling/drop warnings; refined frame timing and config merge; added chmod on config saves; added RobustSerial & framebuffer partial tests | ./venv/bin/pytest -q tests | Partial updates corrected; DFPlayer state safer; touch threshold defaults aligned; new unit coverage.
2025-11-28 | feature/framework-migration | Hardened DFPlayer init cleanup, deferred state until hardware success, shortened listener shutdown, configurable calibration bounds, logging on RobustSerial reconnect, documented deep-merge limits | ./venv/bin/pytest -q tests/unit/test_dfplayer_backend.py tests/unit/test_framebuffer_partial.py tests/unit/test_robust_serial.py | Shutdown more responsive; calibration works across ADC ranges; reconnect errors logged.
2025-11-28 | feature/framework-migration | Added calibration sanity guard, removed optimistic track assignment, adjusted tests, tuned listener timeout messaging | ./venv/bin/pytest -q tests/unit/test_dfplayer_backend.py tests/unit/test_framebuffer_partial.py tests/unit/test_robust_serial.py | Calibration cannot save inverted bounds; DFPlayer state pending until ACK.

2025-12-01 | codebase-review | Comprehensive codebase review and grading across 6 categories (correctness, readability, design, maintainability, testing, Python style) | n/a | Review documented in graded_12-1.md; identified Application god-object and config consolidation as top refactoring priorities.

2025-12-01 | docs-consolidation | Consolidated 40+ documentation files into 5 comprehensive documents | n/a | Reduced clutter while maintaining quality; updated CODING_STANDARDS.md with documentation workflow guidelines.

2025-12-02 | feature/framework-migration | Config consolidation: added typed ApplicationConfig/RuntimeState, bridged legacy Config, updated app to typed paths/volume, refreshed docs, removed deprecated dfplayer_backend | ./venv/bin/pytest -q tests/core/test_application_config_structured.py | Runtime uses src/main.py + app.py; legacy backend removed; docs aligned to unified entrypoint.

2025-12-03 | docs-workflow | Added workflow requirements to AGENTS.md and CLAUDE.md: check TASK_LOG.md before actions, log activities after changes | n/a | Ensures continuity between developers working on the codebase.

2025-12-05 | main | Replaced missing profile select test in CI workflow | not run | Suggested targeted pytest run after workflow update.

2025-12-05 | feature/framework-migration | Touch calibration debugging session: Added visual debug crosshairs, attempted multiple orientation strategies (keep active vs disable), repositioned back buttons to avoid play indicator overlap, increased button spacing to prevent hit area conflicts | Hardware testing | Calibration fundamentally broken - digitizer appears physically rotated 90° but no orientation (1-8) correctly maps all 4 corners. User reports at least one aspect mirrored in all orientations after calibration. Root cause: calibration algorithm assumes standard axis alignment which doesn't match this hardware configuration.
2025-12-05 | feature/framework-migration | Starting diagnostic mode to map touch digitizer coordinate system: Will create raw coordinate logging screen to systematically test corner mapping and determine correct transformation algorithm | Next: Hardware testing | User chose debugging approach over hardcoded values to understand root cause.
2025-12-05 | main | Expanded touch diagnostic screen (multi-event logging, orientation/bounds display) and added unit coverage for history capping/corner mapping; targeted pytest for new file skipped (pytest not available in env) | not run (env lacks pytest) | Run `python -m pytest tests/unit/test_touch_diagnostic.py` after installing test deps.
2025-12-05 | feature/framework-migration | Fixed runtime backend key validation, calibration current_target compatibility, event processor safe attribute reads, artwork path normalization, and DFPlayer shutdown/volume init behavior; tests not run (pytest unavailable) | not run (env lacks pytest) | Run targeted pytest for core/runtime, metadata_security, calibration_edge_cases, event_processor, thread_safety once deps installed.
2025-12-05 | feature/framework-migration | Installed venv deps and ran targeted pytest suite (core config, event processor, calibration edge cases, metadata security, thread safety) | .venv/bin/python -m pytest tests/core/test_application_config_structured.py tests/unit/test_event_processor.py tests/unit/test_calibration_edge_cases.py tests/unit/test_metadata_security.py tests/unit/test_thread_safety.py | 47/47 passed


