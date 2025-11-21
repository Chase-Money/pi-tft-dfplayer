# Gemini Context: pi-tft-dfplayer

This document provides a comprehensive overview of the `pi-tft-dfplayer` project to be used as instructional context for future interactions with the Gemini CLI.

## Project Overview

This project is a DIY touchscreen MP3 player designed for a Raspberry Pi Zero 2 W. It features a direct-to-framebuffer user interface, eliminating the need for a desktop environment (X/Wayland). The application is written in Python and interacts with several hardware components:

*   **Display:** A 3.5" SPI TFT display (ILI9486) for the user interface.
*   **Touch:** A resistive touch controller (XPT2046/ADS7846) for user input.
*   **Audio:** A DFPlayer Mini module for MP3 playback.

The core application (`src/dfplayer_fb_gui.py`) is responsible for:
*   Drawing the UI directly to the framebuffer (`/dev/fb1`).
*   Handling touch input using the `evdev` library.
*   Controlling the DFPlayer Mini over a UART serial connection (`/dev/serial0`).
*   Managing track metadata, artwork, and on-device touch calibration.

The project is designed to be run as a `systemd` service for auto-start on boot.

### Key Technologies

*   **Language:** Python 3
*   **Libraries:**
    *   `Pillow`: For drawing the user interface.
    *   `pyserial`: For communication with the DFPlayer Mini.
    *   `evdev`: For handling touch input.
*   **System:** Runs on Raspberry Pi OS (32-bit). Interacts directly with Linux devices (`/dev/fb1`, `/dev/input/event*`, `/dev/serial0`).

## Building and Running

### 1. Prerequisites

The project requires several system-level dependencies. These can be installed by running the `install_prereqs.sh` script:

```bash
./scripts/install_prereqs.sh
```
This will install `python3-pil`, `python3-serial`, and `python3-dev` using `apt`.

### 2. System Configuration

The project requires some system tweaks to free up the UART for the DFPlayer and to set up a udev rule for the touchscreen. These can be applied by running the `apply_system_tweaks.sh` script:

```bash
./scripts/apply_system_tweaks.sh
sudo reboot
```
This script will:
*   Remove the serial console from the kernel command line (`/boot/cmdline.txt`).
*   Ensure the UART is enabled (`/boot/config.txt`).
*   Copy the udev rule to create a `/dev/input/touchscreen` symlink.

### 3. Running the Application

#### Manual Execution

The application can be run manually for testing purposes:

```bash
sudo -E python3 src/dfplayer_fb_gui.py
```

#### As a Service

To run the application as a `systemd` service that starts on boot:

```bash
sudo cp systemd/dfplayer-fb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dfplayer-fb
```
**Note:** The service file expects the repository to be located at `/home/pi/pi-tft-dfplayer`. If it's cloned elsewhere, the `WorkingDirectory` in the service file must be updated.

## Development Conventions

*   **Testing:** The project uses `pytest` for testing. Test dependencies are listed in `requirements-test.txt`. Tests can be run with the `pytest` command. The test suite includes checks for code quality, duplicate code, and undefined variables. Some tests are hardware-dependent and may not run in a non-target environment.
*   **Configuration:** The application uses a centralized configuration manager (`src/core/config.py`) that loads settings from `~/.dfplayer_config.json`.
*   **Versioning:** A "v2" file versioning policy is in effect. When a file is modified, a new version of that file (e.g., `original_file_v2.py`) should be created with the changes, leaving the original file untouched.
*   **Documentation:** All changes should be clearly documented for future developers.
