# Quick Fix Guide - Renderer Not Writing to Display

## TL;DR

The renderer was silently swallowing errors. The fix makes errors visible.

## Run These Commands on the Pi

```bash
cd ~/projects/pi-tft-dfplayer

# 1. Stop the app
sudo systemctl stop dfplayer-fb

# 2. Check what the hidden error is
./scripts/check_current_app_logs.sh

# 3. Run diagnostics (this will show WHERE it fails)
sudo python3 scripts/diagnose_renderer_bug.py

# 4. Verify the fix works
sudo python3 scripts/verify_renderer_fix.py

# 5. If tests pass, restart the app
sudo systemctl start dfplayer-fb
sudo journalctl -u dfplayer-fb -f
```

## What Was Fixed

**File:** `src/ui/renderer_v2/renderer.py`

**Problem:** The `present()` method caught exceptions but didn't re-raise them, so errors were hidden.

**Fix:** Now validates state, logs detailed info, and re-raises exceptions so you see the real error.

## Most Likely Issues You'll Now See

1. **Permission denied** - Run with sudo or fix udev rules
2. **Wrong framebuffer device** - Use `--fb /dev/fb1` flag
3. **Framebuffer in use** - Stop other processes using /dev/fb1
4. **Size mismatch** - Check framebuffer dimensions

## Quick Test

```bash
# Direct framebuffer write test (bypasses renderer)
sudo python3 << 'EOF'
import sys
sys.path.insert(0, '/home/kiosk/projects/pi-tft-dfplayer/src')
from hardware.framebuffer import Framebuffer
from PIL import Image, ImageDraw

fb = Framebuffer("/dev/fb1")
img = Image.new("RGB", (fb.width, fb.height), (255, 0, 0))
draw = ImageDraw.Draw(img)
draw.text((10, 10), "DIRECT TEST", fill=(255, 255, 255))
fb.push(img)
print("SUCCESS")
fb.close()
EOF
```

If this works, the framebuffer is fine - the issue is in the renderer initialization.

## Enable Debug Logging

Edit `src/main_tft_v2.py` line 35:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

This shows detailed present() logs.

## Contact

See `RENDERER_BUG_FIX.md` for full details.
