# Touchscreen v2 Launcher — Setup

The v2 touchscreen launcher preserves the original UI while swapping imports to v2 modules that fix parent-relative import issues.

## Install

Prerequisites (same as touchscreen path):
- Pillow, evdev, pyserial installed (use `./scripts/install_prereqs.sh`).
- Framebuffer `/dev/fb1` and touch `/dev/input/touchscreen` available (see AGENTS.md).

Install the v2 systemd unit (optional):

```bash
sudo cp systemd/dfplayer-fb-v2.service /etc/systemd/system/
sudo systemctl enable --now dfplayer-fb-v2
```

Manual run:

```bash
python3 src/main_touch_v2.py
```

## How it works

`src/main_touch_v2.py` installs lazy module aliases:
- `utils.calibration` → `utils.calibration_v2`
- `utils.track_catalog` → `utils.track_catalog_v2`
- `backends.dfplayer_backend` → `backends.dfplayer_backend_v2`

Then it imports the original `src/main.py` and executes its `main()` unchanged.

## Troubleshooting

- If import fails due to Pillow/evdev/pyserial, run `./scripts/install_prereqs.sh` and reboot.
- If framebuffer/touch are missing, re-run `./scripts/apply_system_tweaks.sh` and confirm `/dev/fb1` and `/dev/input/touchscreen` exist.

## Hardware Override (Optional)

The touchscreen v2 launcher (`main_touch_v2.py`) does not require any hardware override. If you instead use the profile‑aware entrypoint (`main_v2.py`), you can explicitly select the touchscreen profile:

```bash
# CLI flag takes precedence
python3 src/main_v2.py --hardware ili9486_touch

# Or via environment variable
DFPLAYER_HW_PROFILE=ili9486_touch python3 src/main_v2.py
```

Auto‑detection will also pick the touchscreen when `/sys/class/graphics/fb1/name` reports an ILI948x framebuffer, but explicit selection is useful for diagnostics.
