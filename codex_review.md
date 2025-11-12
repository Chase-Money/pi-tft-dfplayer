# Codex Review: Import regressions break startup (parent‑relative imports)

This review documents the import errors introduced by switching several modules to parent‑relative (`..`) imports while the application continues to load modules as top‑level packages. The result is immediate `ImportError` exceptions ("attempted relative import beyond top‑level package") and a failure to start the app.

## TL;DR
- Multiple modules changed to `from ..X import Y` while callers still import them as top‑level (e.g., `from utils.foo import bar`).
- In this top‑level import context, there is no package parent to traverse, so Python raises `ImportError` on import.
- Restore absolute imports now to unblock runtime. If we want relative imports, we must convert the repo to a real package and change how the app is launched/service is configured.

## Impact
- App fails to start whenever a modified module is imported (backend, calibration, track catalog), blocking core flows like UI launch and calibration.

## Findings (P1)

1) DFPlayer backend switches to parent‑relative
- File: `src/backends/dfplayer_backend.py:9-10`
- Symptom: Importing `backends.dfplayer_backend` (directly or via `src/main.py`) raises:
  - `ImportError: attempted relative import beyond top-level package`
- Root cause: `from ..hardware.dfplayer import DFPlayer` used while `backends` is imported as a top‑level package.
- Fix: Revert to absolute import: `from hardware.dfplayer import DFPlayer`.

2) Calibration module uses invalid parent‑relative imports
- File: `src/utils/calibration.py:12-13`
- Symptom: Importing `utils.calibration` (e.g., `from utils.calibration import run_calibration`) raises the same `ImportError`.
- Root cause: Parent‑relative imports like `from ..hardware.touch import TouchInput` and `from ..hardware.framebuffer import FrameBuffer` while `utils` is imported as top‑level.
- Fix: Revert to absolute imports, e.g., `from hardware.touch import TouchInput`, `from hardware.framebuffer import FrameBuffer`.

3) Track catalog now imports parent‑relative
- File: `src/utils/track_catalog.py:10`
- Symptom: Importing `utils.track_catalog` raises `ImportError`.
- Root cause: `from ..core.state import Track` while `utils` remains top‑level.
- Fix: Revert to absolute import: `from core.state import Track`.

## Root cause
Mixing parent‑relative imports with modules that are imported as top‑level packages. When a module is imported as `from utils.calibration import run_calibration`, `utils` has no parent in the import system, so any `from ..X import Y` inside `utils.foo` tries to climb above the top‑level and fails. Parent‑relative imports only work when the module is part of a real package hierarchy and is itself imported via that hierarchy (e.g., `from pi_tft_dfplayer.utils.foo import bar`).

## Recommendations
Two viable paths. Option A is the minimal, safe fix to restore behavior immediately; Option B is a structural clean‑up that requires changes to how the app is launched and packaged.

### Option A — Revert to absolute imports (ship now)
- Backends: `from hardware.dfplayer import DFPlayer`
- Calibration: `from hardware.touch import TouchInput`, `from hardware.framebuffer import FrameBuffer`
- Track catalog: `from core.state import Track`
- Audit for any additional `from ..` usages and revert them while modules are still imported as top‑level packages.

Validation
```bash
# Find other parent‑relative imports
rg -n "from \.\." src/

# Smoke test imports
python3 - <<'PY'
import importlib
for m in [
    'backends.dfplayer_backend',
    'utils.calibration',
    'utils.track_catalog',
]:
    importlib.import_module(m)
    print('import ok:', m)
PY

# Launch manually (per AGENTS.md instructions)
sudo -E python3 src/dfplayer_fb_gui.py
```

### Option B — Migrate to a real package (then use relative imports consistently)
If we want consistent parent‑relative imports, the project must be imported through a common parent package, and entrypoints must run in package mode.

- Create a package namespace (e.g., `pi_tft_dfplayer`) under `src/` and move modules under it:
  - `src/pi_tft_dfplayer/…` with `__init__.py` files.
- Switch imports to relative within the package (`from ..hardware.dfplayer import DFPlayer`, etc.).
- Run entrypoints via module execution so the package context is established:
  - `python3 -m pi_tft_dfplayer.dfplayer_fb_gui` (or equivalent main module)
- Update systemd unit and docs to use the module invocation instead of a direct script path, or install the package in editable mode:
  - `pip install -e .` with a simple `pyproject.toml` and a console_script if desired.
- Re‑test on the target device; per AGENTS.md, the current unit expects a direct path under `/home/pi/pi-tft-dfplayer`, so this is a breaking change and should be called out if pursued.

## Why this happens (quick primer)
- When a module is imported as top‑level (e.g., `from utils.calibration import run_calibration`), `utils` has no parent package in `__package__`.
- A statement like `from ..hardware.touch import TouchInput` requires `__package__` to include a parent (e.g., `pi_tft_dfplayer.utils`). Without that, Python raises `ImportError: attempted relative import beyond top‑level package` during import.

## Proposed immediate changes (Option A)
Revert the specific imports called out by the review:

- `src/backends/dfplayer_backend.py`
  - Replace: `from ..hardware.dfplayer import DFPlayer`
  - With:    `from hardware.dfplayer import DFPlayer`

- `src/utils/calibration.py`
  - Replace: `from ..hardware.touch import TouchInput`
  - With:    `from hardware.touch import TouchInput`
  - Replace: `from ..hardware.framebuffer import FrameBuffer`
  - With:    `from hardware.framebuffer import FrameBuffer`

- `src/utils/track_catalog.py`
  - Replace: `from ..core.state import Track`
  - With:    `from core.state import Track`

After applying these changes, perform the validation steps above and verify UI, touch calibration, and DFPlayer controls per Testing Guidelines in AGENTS.md.

## Next steps / Acceptance criteria
- No `ImportError: attempted relative import beyond top‑level package` on import of backend, calibration, or track catalog.
- `sudo -E python3 src/dfplayer_fb_gui.py` launches the UI successfully.
- Touch calibration, orientation cycles, and DFPlayer actions function as expected.
- Optional: run `rg -n "from \.\." src/` to ensure no lingering parent‑relative imports remain.

## All review comments (verbatim)
- [P1] Revert parent-relative import in DFPlayer backend — `src/backends/dfplayer_backend.py:9-10`
  Switching the hardware import to `from ..hardware.dfplayer import DFPlayer` breaks module loading because `backends.dfplayer_backend` is imported as a top-level package (see `src/main.py`). When the app is launched as before via `python src/main.py` or any code that does `from backends.dfplayer_backend import DFPlayerBackend`, Python reports `ImportError: attempted relative import beyond top-level package`, preventing the backend (and therefore the whole app) from starting. The import needs to remain absolute (`from hardware.dfplayer import DFPlayer`) unless every other module is also updated to be imported through a common parent package.

- [P1] Calibration module uses invalid parent-relative imports — `src/utils/calibration.py:12-13`
  `src/main.py` imports this module as `from utils.calibration import run_calibration`, meaning `utils` is treated as a top-level package. The new `from ..hardware.touch import TouchInput` / `..hardware.framebuffer` statements therefore try to traverse above the top-level package and immediately raise `ImportError: attempted relative import beyond top-level package` when calibration is imported. This blocks both calibration and any code that imports the module. Keep the absolute imports (`from hardware.touch …`) or change every caller to import through a common parent package first.

- [P1] Track catalog import now crashes due to parent-relative path — `src/utils/track_catalog.py:10`
  `src/main.py` still performs `from utils.track_catalog import load_track_catalog`, so `utils` remains a top-level package. Changing the module to `from ..core.state import Track` means Python attempts to go above the top-level package and raises `ImportError: attempted relative import beyond top-level package` as soon as the catalog loader is imported, preventing the app from booting. This import must stay absolute (`from core.state import Track`) unless the entire project is restructured to import through a higher-level package.

---
If you want, I can apply Option A now (revert the specific imports and audit for any others) and push a follow‑up PR to outline an Option B packaging plan.

