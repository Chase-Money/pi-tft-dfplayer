#!/usr/bin/env bash
set -euo pipefail

# This script disables the Raspberry Pi desktop (lightdm) so /dev/fb1 is free
# for framebuffer apps. It also optionally forces HDMI for X11 and leaves fb1
# dedicated to the TFT.

backup_cfg() {
  local cfg="/boot/firmware/config.txt"
  if [ -f "$cfg" ] && [ ! -f "$cfg.bak" ]; then
    sudo cp "$cfg" "$cfg.bak"
    echo "Backed up $cfg to $cfg.bak"
  fi
}

case "${1:-}" in
  hdmi)
    echo "Disabling lightdm and forcing HDMI output for desktop..."
    sudo systemctl set-default multi-user.target
    sudo systemctl disable lightdm || true
    backup_cfg
    sudo sed -i '/^ignore_lcd=/d' /boot/firmware/config.txt
    sudo sed -i '/^hdmi_force_hotplug=/d' /boot/firmware/config.txt
    echo 'ignore_lcd=1' | sudo tee -a /boot/firmware/config.txt >/dev/null
    echo 'hdmi_force_hotplug=1' | sudo tee -a /boot/firmware/config.txt >/dev/null
    echo "Done. Reboot to apply."
    ;;
  tft-only|"")
    echo "Disabling lightdm so /dev/fb1 is free for framebuffer apps..."
    sudo systemctl set-default multi-user.target
    sudo systemctl disable lightdm || true
    echo "Done. Reboot to apply."
    ;;
  restore)
    echo "Restoring desktop (graphical target + lightdm)..."
    sudo systemctl set-default graphical.target
    sudo systemctl enable lightdm || true
    if [ -f /boot/firmware/config.txt.bak ]; then
      sudo cp /boot/firmware/config.txt.bak /boot/firmware/config.txt
      echo "Restored /boot/firmware/config.txt from backup"
    fi
    echo "Done. Reboot to apply."
    ;;
  *)
    echo "Usage: $0 [tft-only|hdmi|restore]"
    exit 1
    ;;
esac
