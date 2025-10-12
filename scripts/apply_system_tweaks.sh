#!/usr/bin/env bash
set -euo pipefail

# Free UART for DFPlayer (remove serial console on ttyS0)
sudo cp /boot/cmdline.txt /boot/cmdline.txt.bak.$(date +%s)
sudo sed -i 's/console=ttyS0,115200 //g' /boot/cmdline.txt

# Keep UART enabled
grep -q '^enable_uart=1' /boot/config.txt || echo 'enable_uart=1' | sudo tee -a /boot/config.txt

# Optional: prevent screen blanking (harmless on SPI TFT)
grep -q 'consoleblank=0' /boot/cmdline.txt || sudo sed -i '1 s/$/ consoleblank=0/' /boot/cmdline.txt

# udev rule for touchscreen
sudo cp "$(dirname "$0")/../config/95-touchscreen.rules" /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger

echo "Tweaks applied. Reboot recommended."
