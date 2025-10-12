#!/usr/bin/env bash
set -euo pipefail
OUT=SYSTEM.md
{
  echo "# System snapshot"
  date
  echo
  echo "## Kernel"
  uname -a || true
  echo
  echo "## OS"
  cat /etc/os-release || true
  echo
  echo "## Python"
  python3 --version 2>&1 || true
  echo
  echo "## Packages"
  dpkg -l | egrep 'python3-(serial|evdev|pil)|xserver-xorg|fim|fbi' || true
  echo
  echo "## Framebuffer"
  for i in /sys/class/graphics/fb*; do
    n=$(basename "$i")
    echo "### $n"
    for f in name virtual_size bits_per_pixel; do
      printf "  %s: " "$f"; cat "$i/$f"; done 2>/dev/null || true
    echo
  done
  echo "## Input devices"
  ls -l /dev/input/by-* 2>/dev/null || true
} > "$OUT"
echo "Wrote $OUT"
