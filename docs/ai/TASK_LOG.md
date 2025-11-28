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
