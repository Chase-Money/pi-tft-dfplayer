# Waveshare 1.44" ST7735 Variant — Setup Guide

This guide covers the display/input prerequisites and installation steps for the 1.44" button HAT variant.

## Prerequisites

- Enable SPI: add `dtparam=spi=on` to `/boot/config.txt` and reboot.
- Ensure `/dev/spidev0.0` exists; add your user to `spi` and `gpio` groups.
- Install Python bindings and luma.lcd.

## Quick Install

Run the variant installer:

```bash
./scripts/install_st7735_buttons_v2.sh
sudo reboot
```

## Service

Install the variant service alongside the existing touchscreen unit:

```bash
sudo cp systemd/dfplayer-144lcd.service /etc/systemd/system/
sudo systemctl enable --now dfplayer-144lcd
```

The service sets `DFPLAYER_HW_PROFILE=st7735_buttons` and runs `src/main.py`.

## luma.lcd Notes

- Instantiate with `bgr=True` and verify rotation on your HAT.
- API example:
  ```python
  from luma.core.interface.serial import spi
  from luma.lcd.device import st7735
  serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27)
  dev = st7735(serial, width=128, height=128, rotate=0, bgr=True)
  dev.display(pil_image)
  ```

## Backlight PWM (Optional)

- GPIO 24 typically controls backlight. `DisplayST7735` exposes `set_brightness()` and `fade_to()` when RPi.GPIO is available.

## Development without Hardware

- Set `DFPLAYER_USE_EMULATOR=1` to force emulator mode for `DisplayST7735`.
- Unit tests inject fakes for both display and GPIO; no hardware required.

## Hardware Override (Optional)

You can explicitly select the 1.44" button profile using either a CLI flag or an environment variable:

```bash
# CLI flag (highest precedence)
python3 src/main_v2.py --hardware st7735_buttons

# Or environment variable
DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py

# Off-device development with emulator
DFPLAYER_USE_EMULATOR=1 DFPLAYER_HW_PROFILE=st7735_buttons python3 src/main_v2.py
```

If not specified, v3 auto‑detection checks the framebuffer and HAT device‑tree strings and will typically select the correct profile.
