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

License

MIT (see LICENSE)
