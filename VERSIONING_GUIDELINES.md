# Versioning Guidelines (v2)

This repository uses a lightweight file-version convention for significant changes:

- When changing code or scripts, create a new sibling file suffixed with `"_v2"` or `"-v2"` in the filename as appropriate (e.g., `install_st7735_buttons_v2.sh`, `WAVESHARE_144_MIGRATION_PLAN_v2.md`).
- Keep the previous version intact; do not delete or overwrite v1 unless explicitly approved.
- Always ship clear documentation alongside changes (what changed, why, and how to test).
- Default behavior: target the most recent version (highest `vN`) unless otherwise specified by the user.

Scope
- Code files (`.py`, `.sh`), service unit files, and docs that change meaningfully should follow this pattern.
- Tests and new modules that do not replace an existing file can use normal names.

Documentation Requirements
- For every change, update `CHANGES_v2.md` with a brief entry: file path, change summary, testing/validation notes, and migration considerations.
- When adding a new hardware profile or variant, include a setup doc in `docs/` and reference it from the relevant migration plan.

Testing Philosophy
- Favor test-first additions; if a change is testable without hardware, include unit tests with injected fakes/mocks.
- For hardware-only paths, document manual validation steps (commands and expected outputs).

## Transition Plan to Git-First Versioning

This `_vN` convention is intentionally temporary. Once the migration branch with `Application` + `AppState` is verified on hardware:

1. **Freeze the promoted files**: rename `src/main_v3.py` (and other "current" v2/v3 modules) back to their canonical names in a dedicated PR.
2. **Archive legacy entrypoints**: move the superseded `_vN` files to a `legacy/v1` branch so they remain accessible without cluttering `main`.
3. **Switch new work to Git branches**: feature work should land via PRs (e.g., `feature/new-widget`). Avoid introducing new `_vN` siblings unless the production image explicitly depends on the old file.
4. **Document each milestone**: update this file, `CHANGES_v2.md`, and the README with the tag/commit that marked the transition so regressions can be bisected quickly.

Until that cutover happens, continue to log every `_vN` addition plus its rationale/testing notes so we can build a clean history when the repo is normalized.

Examples
- Plan update: `WAVESHARE_144_MIGRATION_PLAN_v2.md`
- New variant installer: `scripts/install_st7735_buttons_v2.sh`
- New variant docs: `docs/st7735_setup.md`, `docs/button_reference.md`
