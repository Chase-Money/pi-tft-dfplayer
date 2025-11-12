"""Framebuffer display module.

Handles direct RGB565 framebuffer rendering for the ILI9486 SPI TFT display.
Provides PIL image to framebuffer conversion and display management.
"""

import logging
import mmap
import os
from PIL import Image

logger = logging.getLogger(__name__)


class Framebuffer:
    """Direct framebuffer interface for RGB565 display.

    Manages memory-mapped framebuffer access and provides RGB888 to RGB565
    little-endian conversion for PIL images.

    Attributes:
        device: Framebuffer device path (default: /dev/fb1)
        width: Display width in pixels
        height: Display height in pixels
    """

    def __init__(self, device='/dev/fb1'):
        """Initialize framebuffer interface.

        Args:
            device: Framebuffer device path
        """
        self.device = device
        self.width, self.height = self._get_fb_size()
        self._fb = None
        self._mm = None
        self._connect()

    def _get_fb_size(self):
        """Read framebuffer size from sysfs.

        Returns:
            tuple: (width, height) in pixels, or (480, 320) if unavailable
        """
        try:
            sysfs_path = f"/sys/class/graphics/{os.path.basename(self.device)}/virtual_size"
            with open(sysfs_path, 'r') as f:
                w, h = map(int, f.read().strip().split(','))
            logger.info(f"Framebuffer size: {w}x{h}")
            return w, h
        except Exception as e:
            logger.warning(f"Could not read framebuffer size: {e}, using default 480x320")
            return 480, 320

    def _connect(self):
        """Open framebuffer device and create memory map."""
        try:
            self._fb = open(self.device, "r+b", buffering=0)
            self._mm = mmap.mmap(
                self._fb.fileno(),
                self.width * self.height * 2,  # 2 bytes per pixel (RGB565)
                mmap.MAP_SHARED,
                mmap.PROT_WRITE
            )
            logger.info(f"Framebuffer {self.device} opened ({self.width}x{self.height})")
        except FileNotFoundError:
            logger.error(f"Framebuffer device {self.device} not found")
            raise
        except PermissionError:
            logger.error(f"Permission denied accessing {self.device}")
            logger.error("Try: sudo usermod -a -G video $USER")
            raise
        except Exception as e:
            logger.error(f"Failed to open framebuffer: {e}")
            raise

    def rgb888_to_rgb565le(self, img):
        """Convert RGB888 PIL image to RGB565 little-endian bytes.

        RGB565 format: RRRRRGGGGGGBBBBB (5 red, 6 green, 5 blue bits)
        Little-endian byte order: [G2G1G0B4B3B2B1B0][R4R3R2R1R0G5G4G3]

        Args:
            img: PIL Image in RGB mode

        Returns:
            bytearray: RGB565 little-endian pixel data
        """
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))

        if img.mode != "RGB":
            img = img.convert("RGB")

        b = img.tobytes()
        out = bytearray(self.width * self.height * 2)
        j = 0

        for i in range(0, len(b), 3):
            # Extract RGB components and pack to 565
            r = b[i] >> 3      # 5 bits
            g = b[i + 1] >> 2  # 6 bits
            bl = b[i + 2] >> 3 # 5 bits

            # Combine into 16-bit value
            v = (r << 11) | (g << 5) | bl

            # Write as little-endian
            out[j] = v & 0xFF
            out[j + 1] = (v >> 8) & 0xFF
            j += 2

        return out

    def push(self, img):
        """Write PIL image to framebuffer.

        Args:
            img: PIL Image to display (will be resized/converted if needed)
        """
        if self._mm is None:
            logger.warning("Framebuffer not initialized, cannot push image")
            return

        try:
            # Convert and write
            rgb565_data = self.rgb888_to_rgb565le(img)
            self._mm.seek(0)
            self._mm.write(rgb565_data)
        except Exception as e:
            logger.error(f"Failed to write to framebuffer: {e}")

    def clear(self, color=(0, 0, 0)):
        """Clear framebuffer to solid color.

        Args:
            color: RGB tuple (default: black)
        """
        img = Image.new("RGB", (self.width, self.height), color)
        self.push(img)

    def close(self):
        """Close framebuffer and memory map."""
        try:
            if self._mm:
                self._mm.close()
                logger.info("Framebuffer memory map closed")
        except Exception as e:
            logger.warning(f"Error closing framebuffer memory map: {e}")

        try:
            if self._fb:
                self._fb.close()
                logger.info("Framebuffer device closed")
        except Exception as e:
            logger.warning(f"Error closing framebuffer device: {e}")

    @property
    def is_open(self):
        """Check if framebuffer is open and ready."""
        return self._mm is not None and self._fb is not None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
