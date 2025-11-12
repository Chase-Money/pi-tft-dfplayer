# v2 Smoke Test Checklist

This checklist validates both the Touchscreen v2 launcher and the 1.44" ST7735 button variant.

## Touchscreen v2 (ILI9486 + touch)

1) Prereqs
- Run `./scripts/install_prereqs.sh` (Pillow, evdev, pyserial)
- Run `./scripts/apply_system_tweaks.sh` and reboot
- Verify `/dev/fb1` exists and `/dev/input/touchscreen` is present

2) Launch
- Manual: `python3 src/main_touch_v2.py`
- Or service: `sudo systemctl enable --now dfplayer-fb-v2`

3) Functional
- Tap CAL and complete 4-point calibration (crosshairs)
- Tap CFG to cycle orientation; ensure UI aligns
- Test Play/Stop/Prev/Next; confirm on-screen volume updates
- Metadata/artwork loads; thumbnails appear without stutter

## 1.44" ST7735 buttons

1) Prereqs
- `./scripts/install_st7735_buttons_v2.sh` then reboot
- Confirm `/dev/spidev0.0` exists; user in `spi` and `gpio` groups

2) Launch
- Manual (emulator off-device): `DFPLAYER_USE_EMULATOR=1 DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py`
- On-device: `sudo cp systemd/dfplayer-144lcd.service /etc/systemd/system/ && sudo systemctl enable --now dfplayer-144lcd`

3) Functional
- Main screen shows track number, title (truncated), and volume bar
- KEY1 toggles play/pause; KEY2 stops; KEY1/KEY2 hold → next/prev
- Joystick UP/DOWN changes track; LEFT/RIGHT adjusts volume; PRESS selects
- Verify color order (BGR) and rotation; adjust in code/service env if needed

4) Optional Enhancements
- Backlight PWM: test `set_brightness()`/`fade_to()` if GPIO 24 wired
- Alphabet jump: long-press UP/DOWN to implement jump-by-letter behavior (future work)

