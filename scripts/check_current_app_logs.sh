#!/bin/bash
# Check current app logs for any hidden errors
# Run this on the Pi to see what's really happening

echo "=========================================="
echo "Checking systemd logs for dfplayer-fb"
echo "=========================================="
echo ""

if systemctl is-active --quiet dfplayer-fb; then
    echo "Service is running"
    echo ""
    echo "Last 100 lines from service log:"
    echo "=========================================="
    sudo journalctl -u dfplayer-fb -n 100 --no-pager
else
    echo "Service is not running"
fi

echo ""
echo ""
echo "=========================================="
echo "Checking for renderer errors"
echo "=========================================="
echo ""
sudo journalctl -u dfplayer-fb -n 200 --no-pager | grep -i "present\|framebuffer\|renderer\|critical\|error" || echo "No renderer errors found"

echo ""
echo ""
echo "=========================================="
echo "Checking Python process"
echo "=========================================="
echo ""
ps aux | grep "python.*main_tft_v2" | grep -v grep || echo "No running process found"

echo ""
echo ""
echo "=========================================="
echo "Current framebuffer status"
echo "=========================================="
echo ""
ls -l /dev/fb1
cat /sys/class/graphics/fb1/virtual_size 2>/dev/null || echo "Cannot read fb1 virtual_size"
cat /sys/class/graphics/fb1/name 2>/dev/null || echo "Cannot read fb1 name"

echo ""
echo ""
echo "=========================================="
echo "Test: Write simple pattern to /dev/fb1"
echo "=========================================="
echo ""
echo "This will test if direct writes work..."

# Create a simple test script
cat > /tmp/test_fb_write.py << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/kiosk/projects/pi-tft-dfplayer/src')

from hardware.framebuffer import Framebuffer
from PIL import Image, ImageDraw

try:
    fb = Framebuffer("/dev/fb1")
    print(f"Framebuffer opened: {fb.width}x{fb.height}")

    img = Image.new("RGB", (fb.width, fb.height), (255, 128, 0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "DIRECT WRITE TEST", fill=(0, 0, 0))

    fb.push(img)
    print("SUCCESS: Direct write completed")
    fb.close()
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
PYTHON_EOF

sudo python3 /tmp/test_fb_write.py
rm /tmp/test_fb_write.py

echo ""
echo "=========================================="
echo "Done"
echo "=========================================="
