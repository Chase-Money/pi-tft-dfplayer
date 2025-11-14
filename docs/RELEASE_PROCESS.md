# Release Process (v2 → Canonical)

This document defines how we publish changes with clear traceability between iterations.

## Goals
- Make it easy to see changes between code versions (Git + GitHub Releases).
- Document each iteration (what changed, why, how to validate, hardware tested).
- Transition v2-suffixed files back to canonical names when stable.

## Workflow

1) Develop in v2 files (transitional safety)
- Implement changes as `*_v2.py` or `*-v2.service` where applicable.
- Add tests where possible (emulator/fake hardware seams).
- Update `CHANGES_v2.md` with:
  - Files changed
  - Summary of changes and rationale
  - Validation steps (commands + expected results)
  - Hardware tested (if any) + notes/screenshots

2) Hardware validation
- Run `docs/smoke_test_checklist_v2.md` on target devices.
- Capture outcomes; attach screenshots or logs to the PR.

3) Migrate to canonical names (when stable)
- Rename/drop `_v2`/`-v2` suffixes.
- Update imports and systemd units.
- Remove alias shims (e.g., `main_touch_v2.py`) after a deprecation window.

4) Tag and publish
- Tag release (Semantic Versioning): `vX.Y.Z`.
- Publish a GitHub Release using `docs/RELEASE_NOTES_TEMPLATE.md` as a guide.
- Link relevant PRs and commits; embed validation notes and screenshots.

5) Deprecation window
- Maintain shims/aliases for one minor version when feasible (e.g., v0.3.x → v0.4.x remove).
- Document removals under “Breaking Changes”.

## References
- `VERSIONING_GUIDELINES.md` — overall strategy
- `CHANGES_v2.md` — iteration log
- `docs/RELEASE_NOTES_TEMPLATE.md` — structure for release notes
- `docs/smoke_test_checklist_v2.md` — validation steps

