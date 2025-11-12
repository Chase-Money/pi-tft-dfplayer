"""
Framebuffer handling for the DFPlayer GUI.
"""

import os
import mmap
from PIL import Image

class Framebuffer:
    def __init__(self, device="/dev/fb1"):
        self.device = device
        self.width, self.height = self._get_size()
        self.fb_file = open(self.device, "r+b", buffering=0)
        self.mm = mmap.mmap(self.fb_file.fileno(), self.width * self.height * 2, mmap.MAP_SHARED, mmap.PROT_WRITE)

    def _get_size(self):
        """Get the framebuffer size from sysfs."""
        try:
            node = f"/sys/class/graphics/{os.path.basename(self.device)}/virtual_size"
            with open(node, "r") as f:
                w, h = map(int, f.read().strip().split(','))
            return w, h
        except Exception:
            return 480, 320

    def _rgb888_to_rgb565le(self, img):
        """Convert an RGB888 image to RGB565 little-endian format."""
        b = img.tobytes()
        out = bytearray(self.width * self.height * 2)
        j = 0
        for i in range(0, len(b), 3):
            r = b[i] >> 3
            g = b[i+1] >> 2
            bl = b[i+2] >> 3
            v = (r << 11) | (g << 5) | bl
            out[j] = v & 0xFF
            out[j+1] = (v >> 8) & 0xFF
            j += 2
        return out

    def push(self, img):
        """Push an image to the framebuffer."""
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))
        self.mm.seek(0)
        self.mm.write(self._rgb888_to_rgb565le(img.convert("RGB")))

    def close(self):
        """Close the framebuffer resources."""
        self.mm.close()
        self.fb_file.close()