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

Once confirmed, we'll generate the corrected config.txt + systemd service file.

---

## Update 2025-11-20: V2 Framework Migration Display Fix

### Issue: V2 App Not Displaying Despite Running Successfully

**Symptoms:**
- V2 app (`src/main_tft_v2.py`) ran at 16 FPS with no errors
- Logs showed successful initialization and rendering
- TFT screen remained blank or showed old content
- Direct test patterns could be written to `/dev/fb1` successfully

**Root Cause:**
The V2 application had **incorrect default framebuffer device** in TWO locations, both defaulting to `/dev/fb0` (HDMI) instead of `/dev/fb1` (TFT):

1. `src/main_tft_v2.py:55` - Class `__init__` parameter default
2. `src/main_tft_v2.py:611` - argparse argument default

### The Fix

**src/main_tft_v2.py:55** (Class constructor):
```python
fb_device: str = "/dev/fb1",  # Changed from /dev/fb0
```

**src/main_tft_v2.py:611** (argparse default):
```python
parser.add_argument("--fb", default="/dev/fb1", help="Framebuffer device (default: /dev/fb1)")
```

**src/main_tft_v2.py:156** (Added diagnostic logging):
```python
logger.info(f"Framebuffer device: {self.framebuffer.device}")
```

### Current Status

✅ **Working:**
- Display shows V2 HomeScreen UI with buttons
- App runs at ~4.8 FPS (functional, though slower than optimized 15 FPS)
- Framebuffer writes correctly to `/dev/fb1`

⚠️ **Known Issues:**
1. **Touch Input Not Responding** - Buttons display but don't react to touches
2. **Performance** - Running at 4.8 FPS vs. expected 15-16 FPS

### For Next Developer: Touch Input Debug

Touch controller initializes successfully:
```
Touch controller initialized
Touch orientation set: swap=True, flip_x=True, flip_y=True
```

But button clicks have no effect. Investigation needed:

1. Add logging in `_process_touch_events()` to see if events are received
2. Check UIEvent creation and routing to screen manager
3. Verify button hit detection with current touch coordinates

**Test touch device directly:**
```bash
sudo evtest /dev/input/touchscreen
# Tap screen - should see ABS_X, ABS_Y events
```

### Files Modified
- `src/main_tft_v2.py` - Fixed framebuffer defaults (lines 55, 611, 156)
- `src/ui/screens_v2/home.py` - Removed debug red rectangle
- `/boot/firmware/cmdline.txt` - Console mapping (`fbcon=map:01`)
