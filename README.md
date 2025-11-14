pi-tft-dfplayer

DIY touchscreen MP3 player for Raspberry Pi Zero 2 W with a 3.5″ SPI TFT (ILI9486 + XPT2046/ADS7846) and a DFPlayer Mini.
Direct-to-framebuffer UI (no X/Wayland), on-device touch calibration, orientation cycling, and UART control of DFPlayer.

Features
	•	Direct /dev/fb1 drawing (RGB565) → fast, no desktop needed
	•	On-device CAL (four-point) and CFG (8 orientations) buttons
	•	Big Play/Prev/Next/Stop controls
	•	Smooth volume bar (0–30) via DFPlayer command 0x06
	•	Systemd service for auto-start

Hardware
	•	Raspberry Pi Zero 2 W (32-bit Pi OS used here)
	•	3.5″ SPI TFT ILI9486 w/ resistive touch XPT2046/ADS7846
	•	DFPlayer Mini (micro-SD with /mp3/0001.mp3, /mp3/0002.mp3, …)
	•	4–8 Ω speaker on DFPlayer SPK+ / SPK-

Wiring (summary)
	•	TFT to SPI0 + its control pins (per your panel’s pinout):
	•	LCD_CS → a free chip-select (often GPIO8/CE0)
	•	LCD_SCK → GPIO11/SCLK
	•	LCD_SI(MOSI) → GPIO10/MOSI
	•	LCD_RS(DC) → a free GPIO (panel doc)
	•	LCD_RST → a free GPIO or Pi reset
	•	5 V and GND to Pi 5 V/GND
	•	Touch (XPT2046/ADS7846) on same SPI bus:
	•	TP_CS → another CS (often GPIO7/CE1)
	•	TP_SCK/TP_SI share SCLK/MOSI, TP_SO to MISO (GPIO9)
	•	TP_IRQ to a free GPIO (optional interrupt)
	•	DFPlayer:
	•	VCC → 5 V, GND → GND
	•	RX  ← Pi TXD0 (GPIO14)
	•	TX  → Pi RXD0 (GPIO15) (optional, for query)
	•	SPK+ / SPK- → speaker

If your panel already exposes a ready-made overlay (e.g., fb_ili9486/ads7846), you should see /dev/fb1 and a touch event* device. This app works as long as those exist.

Software versions (snapshot)

This repo was built/tested on:
	•	Linux kernel: output of uname -a
	•	Pi OS: contents of /etc/os-release
	•	Python: python3 --version
	•	Packages: python3-serial, python3-evdev, python3-pil (Pillow)

You can regenerate a SYSTEM.md with:

./scripts/system_snapshot.sh

Quick start

# 1) Get deps
./scripts/install_prereqs.sh

# 2) Apply system tweaks (frees UART0 for DFPlayer, udev rule for touch)
./scripts/apply_system_tweaks.sh
sudo reboot

After reboot, verify:

ls /dev/fb1
cat /sys/class/graphics/fb1/name        # should mention ili948x
ls /dev/input/event*                     # touch present

Run the app

# manual test
sudo -E python3 src/dfplayer_fb_gui.py

# or enable service
sudo cp systemd/dfplayer-fb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dfplayer-fb

> **Note:** The systemd unit expects this repository to live at
> `/home/pi/pi-tft-dfplayer`. If you clone it elsewhere, update
> `WorkingDirectory` in `systemd/dfplayer-fb.service` (or create a drop-in) so
> the service can locate `src/dfplayer_fb_gui.py`.

Hardware profiles (v2)

This repo now ships v2 launchers for two hardware profiles that run independently of the legacy touchscreen service:

- Touchscreen v2 (3.5" ILI9486 + XPT2046/ADS7846)
  - Manual: `python3 src/main_touch_v2.py`
  - Service: `sudo cp systemd/dfplayer-fb-v2.service /etc/systemd/system/ && sudo systemctl enable --now dfplayer-fb-v2`
  - Setup/troubleshooting: see `docs/touch_v2_setup.md`
  - Experimental screen-manager UI (Phase 2): set `DFPLAYER_UI_FRAMEWORK=1` before running `python3 src/main.py` to launch the new Home/Browser/Now Playing stack built on `ui/framework_v2`

- 1.44" Buttons Variant (ST7735 + GPIO buttons/joystick)
  - Install deps + enable SPI: `./scripts/install_st7735_buttons_v2.sh` then reboot
  - Manual (off-device dev with emulator): `DFPLAYER_USE_EMULATOR=1 DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py`
  - Service (on-device): `sudo cp systemd/dfplayer-144lcd.service /etc/systemd/system/ && sudo systemctl enable --now dfplayer-144lcd`
  - Setup/troubleshooting: see `docs/st7735_setup.md`

## How to Proceed on Your Device (Phase 2 Pilot)

1. **Pick the right launcher**
   - Touchscreen: `sudo -E python3 src/main_touch_v2.py`
   - Button HAT: `DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py` (add `DFPLAYER_USE_EMULATOR=1` on desktops).
2. **Preview the new screen manager** by exporting `DFPLAYER_UI_FRAMEWORK=1` before running `python3 src/main.py`. This now boots the full `src/app_v2.Application` stack (AppState + ScreenManagerV2 + DFPlayer backend) instead of the ad-hoc adapter embedded in `main.py`.
3. **Exercise the Application/AppState stack** via `python3 src/main_v3.py`. This boots `src/app_v2.Application`, initializes the shared AppState + ScreenManagerV2, and is the entrypoint we will promote once the migration branch is merged.
4. **Capture validation details** in `docs/smoke_test_checklist_v2.md` (hardware used, commands run, observations) so the next developer can resume testing exactly where you stopped.

Profile selection

- v2/v3 precedence: CLI flag `--hardware`, then environment variable `DFPLAYER_HW_PROFILE`, then config file key (`hardware.profile`), then auto-detect (fb/hat). Manual override always wins.
- Example: `DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py` or `python3 src/main_v2.py --hardware st7735_buttons`.
- Emulator: set `DFPLAYER_USE_EMULATOR=1` to force the ST7735 display abstraction into emulator mode (helpful off-device).

Smoke tests (v2)

- See `docs/smoke_test_checklist_v2.md` for step-by-step validation of both profiles.
- Quick helper: `./scripts/smoke_test_v2.sh` performs basic import checks and prints the next steps to run on real hardware.

Using the UI
	•	CFG cycles through 8 orientation combos (swap/flip).
	•	CAL shows 4 crosshairs—tap and hold ~0.5 s on each.
	•	Buttons: Play/Prev/Next/Stop; slide the volume bar.

Calibration is saved to ~/.touch_cal.txt.

Repo layout

src/
  dfplayer_fb_gui.py      # main app (direct framebuffer + evdev + DFPlayer UART)
config/
  95-touchscreen.rules    # udev alias: /dev/input/touchscreen
systemd/
  dfplayer-fb.service     # autostart unit
scripts/
  install_prereqs.sh      # apt install Pillow/evdev/serial
  apply_system_tweaks.sh  # UART + udev + console tweaks
  system_snapshot.sh      # dump versions into SYSTEM.md

Troubleshooting
	•	Screen shows boot text over UI
Console mapped to TFT. Fix: in /boot/cmdline.txt change fbcon=map:10 → fbcon=map:01 and reboot.
	•	No /dev/fb1
Overlay/driver not loaded—confirm your TFT overlay (e.g. fb_ili9486) and SPI enabled.
	•	Touch misaligned
Tap CFG until axes feel right, then CAL.
	•	DFPlayer not responding
Ensure console=ttyS0,115200 is removed from /boot/cmdline.txt and enable_uart=1 in /boot/config.txt.

Roadmap
	•	Folder/track browser + “Now Playing”
	•	Optional album art (scaled) from SD
	•	Long-press gestures (seek / fast-volume)
	•	Clean shutdown button (GPIO or long-press)

## Architectural Recommendations

The following recommendations are based on a recent codebase review and refactoring effort. They are intended to guide future development and ensure the project remains maintainable and testable.

### 1. Adopt Git for Version Control

The codebase has recently been refactored from a single script into a more modular, object-oriented architecture (the "v2" implementation). This was a significant improvement, but the "v2" file naming convention should be considered a temporary measure.

**Recommendation:** Use Git branches for feature development and refactoring instead of creating separate `_v2` files. For example, new features should be developed on a feature branch (e.g., `feature/new-ui-component`) and then merged into the main branch after review. This is a more standard and robust approach to version control.

### 2. Expand Test Coverage

The `v2` refactoring introduced a new test suite (`tests/test_v2_logic.py`) that allows for testing the application logic without the need for the actual hardware. This is a major step forward for the project's stability.

**Recommendation:** Continue to expand the test suite to cover more of the application's logic. This should include:
*   Tests for the calibration process (`handle_cal_button`).
*   Edge cases for the track list scrolling and selection.
*   The behavior of the UI when no tracks are available.
*   Tests for the different hardware profiles.

### 3. Continue to Refine the Architecture

The `v2` architecture provides a solid foundation for future development. As new features are added, this modular structure should be maintained and refined.

**Recommendation:**
*   **Simplify the Main Loop:** The `run` method in `dfplayer_fb_gui_v2.py` is the most complex part of the application. Future refactoring efforts should focus on simplifying this loop by further abstracting the event handling logic. For example, a dedicated `EventHandler` class could be created to process touch events and delegate them to the appropriate UI components.
*   **Enhance UI Components:** If the UI is expected to grow in complexity, consider creating a more robust UI component system or evaluating a library like `pygame` (configured to use the framebuffer backend).

### 4. Transition from `_vN` Files to Branch-Based Versioning

The file-based versioning convention (keeping `*_v2.py`, `*_v3.py`, etc.) is useful while Phase 2 is still actively comparing the legacy touchscreen stack with the new Application/AppState code. Once `src/main_v3.py` and the ScreenManagerV2 UI are validated on hardware, freeze that implementation on `main` and archive older entrypoints on a `legacy/v1` branch.

- Continue creating `_vN` siblings only when the legacy runtime still needs the previous file untouched (e.g., `main.py` for the existing systemd unit).
- New features should be developed on Git branches (e.g., `feature/gesture-support`) and merged through PRs. Document each merge in `CHANGES_v2.md` so every iteration remains traceable.
- During the cutover, tag the commit that finalizes `_vN` files and document the transition in `VERSIONING_GUIDELINES.md` so regressions can be bisected quickly.

By following these recommendations, the project will be well-positioned for future growth and will remain a stable and maintainable codebase.

License

MIT (see LICENSE)
- Tests (v2)

- See `tests/README_v2.md` for the modular test suite covering selectors, display/input abstractions, UI helpers, the screen manager, and the touchscreen v2 launcher bootstrap.
- Legacy tests for the monolithic `dfplayer_fb_gui.py` remain documented in `tests/README.md` and may require hardware packages (evdev) to pass on non-Pi systems.
- Install once for local dev/tests: `pip install -e .` (uses `pyproject.toml`). After that, `python -m pytest -q tests/...` works out of the box, and GitHub Actions runs the same suite automatically on every push/PR.
- If you prefer the classic flow, `pip install -r requirements.txt` installs the runtime deps (Pillow, pyserial, evdev) without the editable extras.
