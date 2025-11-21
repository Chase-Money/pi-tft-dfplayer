# Waveshare 1.44" LCD HAT Migration Plan — v2

Status: Updated per review feedback. This version reconciles estimates, clarifies SPI/luma installs, aligns entrypoint/service usage for this repo, specifies PRESS/HOLD behavior, details hardware detection nuances, and includes optional enhancements.

## Executive Summary

Recommendation unchanged: implement as a separate variant branch with experimental status. The 128×128, button‑driven UX is a fundamental paradigm shift from the 480×320 touchscreen. Treat this as a hardware profile/variant, not a replacement.

Key changes in v2:
- Installation details include enabling SPI, needed packages, and group memberships.
- luma.lcd API notes for device instantiation and rotation/BGR.
- PRESS vs HOLD policy to avoid double‑fire.
- Entry point aligned with repo conventions and systemd unit added for the variant.
- Hardware detection guidance for device‑tree reading (binary decode) and override precedence.
- Estimates reconciled to a single range and broken down consistently.
- Optional enhancements added (backlight PWM, alphabet jump, simple emulator).

---

## 1. Feasibility & Scope

- Technical feasibility: High (DFPlayer + new display/input abstraction)
- UX feasibility: Moderate‑Low (severe density tradeoffs on 128×128)
- Variant scope: New display and input layers, major UI redesign, config and docs split.

Reusable modules: backends/dfplayer_backend.py, hardware/dfplayer.py, core/config.py (minus touch methods), core/state.py (plus small UI state additions), core/events.py, utils/metadata.py, utils/track_catalog.py.

---

## 2. Architecture Changes

### 2.1 Hardware — Display (ST7735S)

Library: luma.lcd with SPI.

SPI prerequisites:
- Enable SPI: add `dtparam=spi=on` to `/boot/config.txt`, reboot.
- Ensure `/dev/spidev0.0` exists; add user to `spi` and `gpio` groups.
- Packages (Debian/Raspbian): `python3-spidev`, `python3-rpi.gpio`, and either `python3-luma.lcd` (apt) or `pip install luma.lcd`.

Instantiation notes (luma.lcd):
- Typical: `from luma.core.interface.serial import spi` and `from luma.lcd.device import st7735`.
- Example: `serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)`; then `st7735(serial, width=128, height=128, rotate=0, bgr=True)`.
- Rotation and BGR need empirical verification on the Waveshare HAT.

API abstraction: `DisplayST7735` with `.push(img_like)`, `.clear(color)`, optional `.set_brightness(percent)` and `.fade_to(percent, ms)` (PWM on GPIO 24 where available). Provide a no‑hardware emulator path for development.

### 2.2 Hardware — Input (Buttons + Joystick)

Library: RPi.GPIO.

Buttons/joystick mapping (BCM):
- KEY1=21, KEY2=20, KEY3=16; UP=6, DOWN=19, LEFT=5, RIGHT=26, PRESS=13.

PRESS vs HOLD policy:
- HOLD threshold: 350 ms default, configurable.
- If HOLD fires, suppress PRESS for that press cycle (no double‑fire).
- Debounce: 50 ms software debounce (plus optional hardware).

API abstraction: `ButtonInput` with callback registration for PRESS/RELEASE/HOLD and a polling loop fallback when edge‑detect isn’t available. Inject GPIO dependency for testability.

### 2.3 UI & Entry Point

Entry point: keep `src/main.py` as the modern modular entry for the variant service. Existing `src/dfplayer_fb_gui.py` remains for the 3.5" path.

UI strategy (128×128):
- Minimal layouts, high contrast, bold fonts, aggressive truncation.
- Dedicated screens: MAIN, TRACK_LIST (2 rows visible), VOLUME, INFO, SETTINGS.
- Icons instead of text where possible. Target render < 100 ms.

### 2.4 Config & Detection

Profile selection precedence: CLI flag > env var (`DFPLAYER_HW_PROFILE`) > config file key > auto‑detect.

Auto‑detect guidance:
- Read `/proc/device-tree/hat/product` as binary and decode UTF‑8, strip nulls. Example:
  ```python
  with open('/proc/device-tree/hat/product', 'rb') as f:
      prod = f.read().decode('utf-8', 'ignore').strip('\x00').lower()
  ```
- For framebuffer, check `/sys/class/graphics/fb1/name` for `ili9486`.
- Always allow manual override even if auto‑detect finds something.

Separate config files:
- `config/ili9486_touch.json` and `config/st7735_buttons.json` with hardware‑specific keys.

---

## 3. Implementation Phases (Reconciled Estimates)

Total: 80–92 hours (10–11.5 days). Breakdown:

Phase 1 — Hardware Abstractions (16–20 h)
- DisplayST7735 with luma.lcd + emulator path.
- ButtonInput with debounce, press/hold policy, and poll/interrupt backends.
- New tests with mocks for both modules.

Phase 2 — UI Redesign (22–26 h)
- Layouts for MAIN/TRACK_LIST/VOLUME/INFO.
- Rendering tuned for readability/performance.
- Icons/typography and truncation logic.

Phase 3 — Input Integration (14–16 h)
- Context‑aware routing, button mapping, long‑press actions (alphabet jump).
- Event bus wiring and UI updates.

Phase 4 — Integration & Testing (20–22 h)
- End‑to‑end wiring on device, performance tuning, stability.
- Systemd unit, install scripts, docs.

Phase 5 — Polish (8 h)
- UX refinement, error handling, backlight PWM fades, docs.

---

## 4. Risks & Mitigations (Key Additions)

- SPI enablement and group memberships documented and automated via script.
- PRESS/HOLD double‑fire eliminated by suppressing PRESS on HOLD.
- luma.lcd API version differences called out; test on device early.
- Emulator path unblocks dev/CI without hardware.

---

## 5. Installation & Service (Variant)

Script: `scripts/install_st7735_buttons_v2.sh`
- Enables SPI, installs `python3-spidev`, `python3-rpi.gpio`, and luma.lcd (apt or pip), ensures group membership for `spi` and `gpio`.
- Notes font packages if not present (DejaVu).

Service: `systemd/dfplayer-144lcd.service`
- Mirrors existing service conventions, sets `DFPLAYER_HW_PROFILE=st7735_buttons`, runs `src/main.py`.

---

## 6. Optional Enhancements

- Backlight PWM: control GPIO 24 with PWM for brightness, idle dimming, and fades.
- Alphabet jump: hold UP/DOWN to jump by initial letter; optionally long‑press KEY3 to open a “jump to letter” overlay.
- Emulator: off‑hardware fallback that writes frames to a temp folder or in‑memory sink for tests; optionally a simple Tk window if X is available.

---

## 7. Deliverables in this patch

- New skeletons: `src/hardware/display_st7735.py`, `src/hardware/button_input.py` with mockable seams and docstrings.
- Tests: `tests/hardware/test_display_st7735.py`, `tests/hardware/test_button_input.py` use injected fakes (no hardware required).
- Install script: `scripts/install_st7735_buttons_v2.sh` with SPI enablement and deps.
- Service unit: `systemd/dfplayer-144lcd.service` aligned with repo conventions.
- Docs: `docs/st7735_setup.md`, `docs/button_reference.md`.

---

## 8. Next Steps

1) Validate on device: SPI, colors (BGR), rotation, and button mapping.
2) Implement the 128×128 UI layouts and input routing.
3) Wire profile selection (env/config/CLI) in `src/main.py` or a thin launcher.
4) Iterate on UX and performance targets (<100 ms render, <100 ms button response).

