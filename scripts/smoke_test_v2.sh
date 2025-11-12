#!/usr/bin/env bash
set -euo pipefail

echo "[smoke] Python: $(python3 --version 2>/dev/null || echo missing)"

echo "[smoke] Import core.profile_select_v2"
python3 - <<'PY'
import importlib
import sys, os
sys.path.insert(0, 'src')
mod = importlib.import_module('src.core.profile_select_v2')
disp, inp = mod.select_hardware('st7735_buttons')
print('profile_select ok:', disp, inp)
PY

echo "[smoke] Display emulator import (no hardware)"
DFPLAYER_USE_EMULATOR=1 python3 - <<'PY'
import importlib, sys
sys.path.insert(0, 'src')
disp_mod = importlib.import_module('src.hardware.display_st7735')
D = disp_mod.DisplayST7735
dev = D(use_emulator=True)
print('display init ok (emulator)')
dev.clear((10,20,30))
print('display clear ok')
dev.close()
print('display close ok')
PY

cat <<'TXT'
[smoke] Touchscreen v2 check
- Ensure Pillow/evdev/pyserial installed: ./scripts/install_prereqs.sh
- Ensure /dev/fb1 and /dev/input/touchscreen exist
- Then run: python3 src/main_touch_v2.py (on device)

[smoke] 1.44" buttons check
- Ensure SPI enabled and deps installed: ./scripts/install_st7735_buttons_v2.sh (then reboot)
- On device service: sudo systemctl enable --now dfplayer-144lcd
- Off-device dev: DFPLAYER_USE_EMULATOR=1 DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py
TXT

echo "[smoke] Done"

