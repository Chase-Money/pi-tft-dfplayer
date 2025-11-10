# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DIY touchscreen MP3 player for Raspberry Pi Zero 2 W with a 3.5″ SPI TFT display (ILI9486 + XPT2046/ADS7846 touch controller) and DFPlayer Mini module. This is a direct-to-framebuffer application (no X/Wayland) that provides a touch UI for controlling music playback.

## Hardware Architecture

- **Display**: 3.5″ ILI9486 SPI TFT at /dev/fb1 (RGB565 format)
- **Touch**: XPT2046/ADS7846 resistive touch controller via evdev
- **Audio**: DFPlayer Mini via UART0 (/dev/serial0 at 9600 baud)
- **Platform**: Raspberry Pi Zero 2 W running 32-bit Pi OS

## Key Commands

### Setup and Installation
```bash
# Install dependencies
./scripts/install_prereqs.sh

# Apply system configuration (frees UART0, sets up udev)
./scripts/apply_system_tweaks.sh
sudo reboot

# Verify hardware
ls /dev/fb1
cat /sys/class/graphics/fb1/name
ls /dev/input/event*
```

### Running the Application
```bash
# Manual test run
sudo -E python3 src/dfplayer_fb_gui.py

# Install and enable systemd service
sudo cp systemd/dfplayer-fb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dfplayer-fb

# Check service status
sudo systemctl status dfplayer-fb

# View logs
sudo journalctl -u dfplayer-fb -f
```

### System Snapshot
```bash
# Generate SYSTEM.md with version information
./scripts/system_snapshot.sh
```

## Code Architecture

### Main Application (src/dfplayer_fb_gui.py)

Single-file application with distinct functional sections:

1. **Framebuffer Management** (lines 334-349)
   - Direct RGB565 framebuffer writes to /dev/fb1 via mmap
   - `rgb888_to_rgb565le()`: Converts PIL RGB images to RGB565 little-endian format
   - `push()`: Writes rendered UI to framebuffer

2. **Touch Input System** (lines 299-331, 529-604)
   - Uses evdev to read raw touch coordinates from XPT2046/ADS7846
   - Supports 8 orientation configurations (SWAP_XY, FLIP_X, FLIP_Y combinations)
   - Four-point calibration system saves to ~/.touch_cal.txt
   - `scale_xy()`: Transforms raw touch coordinates to screen coordinates
   - Median filtering of touch samples for stability

3. **DFPlayer UART Protocol** (lines 92-99)
   - Custom serial protocol with checksums
   - Key commands: 0x0F (play folder), 0x01 (next), 0x02 (prev), 0x06 (volume), 0x16 (stop)
   - `send()`: Constructs 10-byte packets with 16-bit checksum
   - Volume range: 0-30

4. **Track Management** (lines 162-298)
   - Track catalog loaded from text file (number|title format)
   - Scrollable track list with visual feedback
   - Track selection and playback state tracking
   - `play_track_number()`: Sends DFPlayer command to play specific track
   - `advance_track()`: Navigate prev/next through catalog

5. **Metadata & Artwork** (lines 36-161)
   - JSON metadata at /boot/dfplayer_metadata.json or DFPLAYER_METADATA env var
   - Album artwork loading and caching with thumbnail generation
   - Artwork displayed in 200x200 region with LANCZOS resampling
   - Track info region shows title/artist/track number

6. **UI Rendering** (lines 351-527)
   - PIL-based UI with rounded rectangles and custom fonts
   - Main controls: Play/Prev/Next/Stop buttons
   - Volume slider with drag gesture support
   - Track list panel with scroll buttons
   - CAL/CFG buttons for calibration and orientation cycling

7. **Main Event Loop** (lines 605-738)
   - Processes evdev touch events continuously
   - Median-filtered touch coordinates (6-sample window)
   - Gesture detection for buttons, volume slider, track list
   - Touch state machine with drag detection

### Configuration Files

- **config/95-touchscreen.rules**: udev rule creating /dev/input/touchscreen symlink
- **systemd/dfplayer-fb.service**: Systemd unit expecting repository at /home/pi/pi-tft-dfplayer

### Scripts

- **install_prereqs.sh**: Installs python3-pil, python3-serial, python3-evdev
- **apply_system_tweaks.sh**: Removes console=ttyS0 from cmdline.txt, enables UART, installs udev rule
- **system_snapshot.sh**: Documents system versions

## Critical Implementation Details

### Touch Coordinate Transformation Pipeline
Raw touch → orientation transform (swap/flip) → calibration scaling → screen coordinates. All transformations in `scale_xy()` must maintain consistency with calibration in `quick_calibration()`.

### DFPlayer Communication
DFPlayer expects files organized as /mp3/0001.mp3, /mp3/0002.mp3 on its micro-SD card. Track numbers sent via UART must match filesystem numbering.

### Framebuffer Format
Direct RGB565 little-endian writes. Each pixel is 2 bytes: `[G2G1G0B4B3B2B1B0][R4R3R2R1R0G5G4G3]`. No double buffering - render complete frame before push().

### Service Location Constraint
Systemd service WorkingDirectory is hardcoded to /home/pi/pi-tft-dfplayer. If repository is cloned elsewhere, update the service file or create a systemd drop-in override.

## Environment Variables

- `DFPLAYER_METADATA`: Path to metadata JSON (default: /boot/dfplayer_metadata.json)
- `DFPLAYER_ART_ROOT`: Base directory for relative artwork paths
- `DFPLAYER_TRACK_CATALOG`: Path to track catalog file

## Development Notes

### Testing Without Hardware
The application requires physical hardware (/dev/fb1, touch device, DFPlayer UART). Cannot run on standard desktop systems. Consider adding a mock/simulator mode for development.

### UI Layout Constants
Screen geometry is fixed at framebuffer dimensions (typically 480x320). Button positions and sizes are hardcoded. When modifying layout, update both drawing code and touch hit detection regions.

### Passphrase
The passphrase for this project is: RAurelius2020<3
