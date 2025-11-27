import mmap
import tempfile

import numpy as np
from PIL import Image

from hardware.framebuffer import Framebuffer


def _make_framebuffer(width=4, height=3):
    """Create a Framebuffer instance backed by an in-memory mmap for testing."""
    fb = Framebuffer.__new__(Framebuffer)
    fb.device = "/dev/fake"
    fb.width = width
    fb.height = height
    fb._rgb565_buffer = np.empty((height, width), dtype=np.uint16)

    tmp = tempfile.TemporaryFile()
    tmp.truncate(width * height * 2)
    fb.fb_file = tmp
    fb.mm = mmap.mmap(tmp.fileno(), width * height * 2, access=mmap.ACCESS_WRITE)
    return fb


def test_push_partial_writes_correct_rows():
    fb = _make_framebuffer(4, 3)
    img = Image.new("RGB", (4, 3), (0, 0, 0))

    # Set a 2x2 region with unique colors to validate row placement
    colors = [  # (x, y, (r, g, b))
        (1, 1, (10, 20, 30)),
        (2, 1, (40, 50, 60)),
        (1, 2, (70, 80, 90)),
        (2, 2, (100, 110, 120)),
    ]
    for x, y, c in colors:
        img.putpixel((x, y), c)

    fb.push_partial(img, (1, 1, 2, 2))

    # Build expected framebuffer bytes
    region = img.crop((1, 1, 3, 3)).convert("RGB")
    buf = fb._rgb888_to_rgb565le(region)

    expected = bytearray(fb.width * fb.height * 2)
    for row_idx, row in enumerate(range(1, 3)):
        offset = (row * fb.width + 1) * 2
        expected[offset: offset + 4] = buf[row_idx, :].tobytes()

    fb.mm.seek(0)
    actual = fb.mm.read()

    fb.mm.close()
    fb.fb_file.close()

    assert actual == bytes(expected)
