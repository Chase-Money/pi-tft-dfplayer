# Repository Guidelines

## Project Structure & Module Organization
Source lives under `src/`, with `dfplayer_fb_gui.py` handling framebuffer drawing, evdev touch input, and DFPlayer UART traffic. Deployment helpers stay in `scripts/`: install prerequisites, apply UART/touch tweaks, and snapshot the host system. Hardware-facing configuration files reside in `config/` (udev aliases) and `systemd/` (auto-start unit expecting `/home/pi/pi-tft-dfplayer`). Keep new assets beside the modules that consume them.

## Build, Test, and Development Commands
Run `./scripts/install_prereqs.sh` once to pull Python dependencies (Pillow, evdev, pyserial). Apply kernel/udev tweaks with `./scripts/apply_system_tweaks.sh` and reboot so `/dev/fb1` and `touchscreen` appear. Launch the UI manually via `sudo -E python3 src/dfplayer_fb_gui.py`; use `DFPLAYER_METADATA=/boot/dfplayer_metadata.json` or `DFPLAYER_ART_ROOT=...` to point at custom assets. Enable the long-running service with `sudo systemctl enable --now dfplayer-fb` after copying it into `/etc/systemd/system/`.

## Coding Style & Naming Conventions
Stick to Python 3.9+, 4-space indentation, and module-level constants in `SCREAMING_SNAKE_CASE` like `FB`, `ORIENTS`, and `ART_RECT`. Functions and variables use descriptive `snake_case`; keep UART or GPIO helpers focused and side-effect free. Prefer small, single-purpose functions (e.g., `load_metadata`, `update_artwork_cache`) and keep touch or framebuffer math documented inline. When adding files, include an encoding-safe `utf-8` read/write path and guard hardware access with try/except blocks.

## Testing Guidelines
Automated tests do not yet exist, so rely on manual runs. Before submitting changes, verify `/dev/fb1` reports the correct driver, confirm touch calibration (tap CAL and hold each crosshair), and cycle orientations until UI aligns. Exercise DFPlayer actions (Play/Prev/Next/Stop) and check volume updates the on-screen bar. If you alter metadata or artwork logic, set a temporary `DFPLAYER_METADATA` path and confirm artwork thumbnails refresh without blocking the UI.

## Commit & Pull Request Guidelines
Use short, imperative subject lines that start with the touched subsystem, e.g., `touch: persist calibration JSON` or `service: honor custom repo path`. Reference related docs or scripts in the body when behavior changes hardware expectations. PRs should outline the user impact, list validation steps (commands run, hardware verified), and attach screenshots or framebuffer captures if UI elements move. Flag any breaking changes to systemd units or config defaults.

## Security & Configuration Tips
Never commit device-specific secrets, Wi-Fi credentials, or `/boot/config.txt` snapshots. Update `config/95-touchscreen.rules` or `systemd/dfplayer-fb.service` via drop-ins rather than editing distro files in-place, and document any extra GPIO or UART pins you use. When introducing new environment variables, give them safe defaults and note them in `README.md` so installers know which settings must be exported before launching the UI.
