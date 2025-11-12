#!/usr/bin/env bash
set -euo pipefail

# Waveshare 1.44" ST7735 button HAT prerequisites (variant)
# - Enables SPI
# - Installs GPIO/SPI Python bindings and luma.lcd
# - Adds current user to spi/gpio groups
# - (Optional) installs DejaVu fonts used by the UI

echo "[st7735] Enabling SPI in /boot/config.txt (requires reboot)"
if ! grep -q '^dtparam=spi=on' /boot/config.txt; then
  echo 'dtparam=spi=on' | sudo tee -a /boot/config.txt >/dev/null
fi

echo "[st7735] Installing packages (python3-spidev, python3-rpi.gpio, luma.lcd)"
sudo apt update
sudo apt install -y python3-spidev python3-rpi.gpio python3-pip

# Prefer apt package if available; fall back to pip for luma.lcd
if ! python3 -c 'import luma.lcd' 2>/dev/null; then
  if apt-cache show python3-luma.lcd >/dev/null 2>&1; then
    sudo apt install -y python3-luma.lcd
  else
    pip3 install --break-system-packages --upgrade luma.lcd
  fi
fi

echo "[st7735] Adding user ${USER} to spi,gpio groups"
if id -nG "$USER" | grep -vq '\bspi\b'; then sudo usermod -a -G spi "$USER"; fi
if id -nG "$USER" | grep -vq '\bgpio\b'; then sudo usermod -a -G gpio "$USER"; fi

echo "[st7735] Ensuring DejaVu fonts are installed (optional)"
sudo apt install -y fonts-dejavu-core || true

echo "Done. Reboot recommended to apply SPI and group changes."

