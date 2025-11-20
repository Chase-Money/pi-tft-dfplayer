# TFT_DEBUG_LOG.md

## Overview
This file documents the behavior of the Raspberry Pi 3.5" SPI TFT (ILI9486 + ADS7846) during development of the DFPlayer framebuffer GUI. The TFT initializes, but the DFPlayer app cannot draw to the display.

## Hardware
- Raspberry Pi (Raspberry Pi OS using `/boot/firmware/`)
- 3.5" SPI TFT  
  - Display driver: `fb_ili9486`  
  - Touch driver: `ads7846`
- Uses `/dev/fb1` as SPI framebuffer

## Current Symptoms
- Screen powers on and shows kernel boot text.  
- After boot, the TFT shows the *Raspberry Pi Desktop splash screen* (GUI).  
- DFPlayer app runs (speaker “click” on init), but nothing appears on-screen.  
- Direct writes to `/dev/fb1` using `dd` show **no visible change**.

## What We Verified
- `/dev/fb1` exists (correct resolution).
- Kernel drivers load successfully:
  - `fb_ili9486` bound to SPI0.0
  - `ads7846` bound to SPI0.1
- Direct framebuffer writes execute without error.
- DFPlayer code selects `/dev/fb1` properly.
- Systemd service starts normally.

## Root Cause
**The Raspberry Pi Desktop (X11/KMS) is rendering to the SPI framebuffer `/dev/fb1`, overwriting all output from the DFPlayer framebuffer app.**

Framebuffer apps cannot run on the same device as the X11 desktop.

## Required Fix
Disable the desktop environment so it no longer claims `/dev/fb1`.

Run:
```
sudo systemctl set-default multi-user.target
sudo systemctl disable lightdm
sudo reboot
```

After reboot:
- TFT should stop loading the desktop environment.
- `/dev/fb1` will remain free for the DFPlayer GUI.
- Your framebuffer app should render correctly.

## Optional Alternative (Desktop on HDMI only)
If you want GUI on HDMI but framebuffer on TFT:

Add to `/boot/firmware/config.txt`:
```
ignore_lcd=1
hdmi_force_hotplug=1
```

This forces X11 onto HDMI and reserves `/dev/fb1` for your app.

## Next Actions
- Confirm whether you want:
  1. TFT-only framebuffer system (recommended)  
  2. Desktop on HDMI, TFT for framebuffer app

Once confirmed, we’ll generate the corrected config.txt + systemd service file.
