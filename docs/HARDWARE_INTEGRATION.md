# Hardware Integration

This document consolidates all hardware-specific documentation, setup guides, and integration details for the pi-tft-dfplayer project.

## Hardware Architecture

### Raspberry Pi Zero 2 W Specifications
- **CPU:** Quad-core ARM Cortex-A53 @ 1GHz
- **RAM:** 512MB LPDDR2
- **Display:** 3.5″ ILI9486 SPI TFT (480×320, RGB565)
- **Touch:** XPT2046/ADS7846 resistive touchscreen
- **Audio:** DFPlayer Mini via UART0 (/dev/serial0)
- **OS:** Raspberry Pi OS (32-bit)

### Component Connections

```
Raspberry Pi Zero 2 W
├── SPI0 (/dev/spidev0.0)
│   └── ILI9486 TFT Display (/dev/fb1)
├── GPIO (Touch Interrupts)
│   └── XPT2046 Touch Controller
├── UART0 (/dev/serial0)
│   └── DFPlayer Mini MP3 Module
└── I2C (Optional)
    └── Future: GPIO expanders, sensors
```

## Display Integration (ILI9486)

### Framebuffer Setup
- **Device:** `/dev/fb1`
- **Resolution:** 480×320 pixels
- **Color Format:** RGB565 (16-bit)
- **Memory:** Direct mmap access for performance

### Display Configuration
```bash
# Verify display detection
ls /dev/fb1
cat /sys/class/graphics/fb1/name  # Should show ILI9486

# Check framebuffer info
fbset -fb /dev/fb1
```

### RGB565 Format Details
- **Pixel Format:** `[G2G1G0B4B3B2B1B0][R4R3R2R1R0G5G4G3]`
- **Byte Order:** Little-endian
- **Conversion:** PIL RGB888 → RGB565 via custom function
- **Performance:** Direct memory writes, no double buffering

## Touch Input (XPT2046/ADS7846)

### Touch Controller Setup
- **Interface:** SPI with interrupt GPIO
- **Resolution:** 12-bit ADC (0-4095 range)
- **Calibration:** 4-point calibration system
- **Orientation:** 8 possible orientations (SWAP_XY, FLIP_X, FLIP_Y combinations)

### Touch Configuration
```bash
# Check touch device detection
ls /dev/input/event*

# Verify udev rules
cat /etc/udev/rules.d/95-touchscreen.rules

# Test touch input
evtest /dev/input/touchscreen
```

### Calibration Process
1. **Raw Coordinates:** Controller provides 0-4095 range
2. **Orientation Transform:** Apply SWAP_XY, FLIP_X, FLIP_Y
3. **Calibration Scaling:** Map to screen coordinates (0-479, 0-319)
4. **Median Filtering:** 6-sample window for stability

### Touch Thresholds
- **Tap Threshold:** 400ms maximum duration
- **Drag Threshold:** 12 pixels minimum movement
- **Swipe Threshold:** 70 pixels minimum distance
- **Debounce:** 100ms minimum between taps

## DFPlayer Mini Audio Module

### Hardware Interface
- **Communication:** UART serial at 9600 baud
- **Protocol:** Custom 10-byte packet format with checksum
- **Commands:** Play, pause, stop, volume, track selection
- **Responses:** Asynchronous status messages

### DFPlayer Limitations
**Critical Understanding:** DFPlayer Mini is a **STANDALONE Module**
- ❌ Cannot read files from DFPlayer's SD card
- ❌ Cannot see filenames on DFPlayer's SD card
- ❌ Cannot access DFPlayer's filesystem
- ❌ Cannot know what files exist without querying

### File Organization Requirements
```
DFPlayer SD Card Structure:
/mp3/
├── 0001.mp3  (Track 1)
├── 0002.mp3  (Track 2)
├── 0003.mp3  (Track 3)
└── ...
```

### UART Communication
```python
# Command packet format (10 bytes)
[0x7E, 0xFF, 0x06, CMD, 0x00, P1, P2, 0x00, 0x00, 0xEF]

# Checksum calculation
total = sum(payload[1:7]) & 0xFFFF
checksum = (0xFFFF - total + 1) & 0xFFFF
```

## System Configuration

### UART0 Setup
```bash
# Disable console on UART0 (in /boot/cmdline.txt)
# Remove: console=ttyS0,115200
# This frees UART0 for DFPlayer communication
```

### SPI Setup
```bash
# SPI must be enabled for display and touch
# Check: raspi-config -> Interfacing Options -> SPI
```

### I2C Setup (Optional)
```bash
# Enable I2C for future expansion
# raspi-config -> Interfacing Options -> I2C
```

### udev Rules
```bash
# Create touchscreen symlink
cat > /etc/udev/rules.d/95-touchscreen.rules << 'EOF'
SUBSYSTEM=="input", KERNEL=="event*", ATTR{name}=="*touchscreen*", SYMLINK+="input/touchscreen"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Hardware Setup Scripts

### Prerequisites Installation
```bash
#!/bin/bash
# scripts/install_prereqs.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3-pip python3-pil python3-serial

# Install evdev (Linux only)
pip3 install evdev

# Install development tools
pip3 install black isort flake8 mypy
```

### System Tweaks
```bash
#!/bin/bash
# scripts/apply_system_tweaks.sh

# Disable console on UART0
sudo sed -i 's/console=ttyS0,[0-9]* //g' /boot/cmdline.txt

# Install udev rules
sudo cp config/95-touchscreen.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Reboot required for UART0 changes to take effect"
```

## Hardware Validation

### Display Testing
```bash
# Test framebuffer access
python3 -c "
import mmap
with open('/dev/fb1', 'r+b') as f:
    mm = mmap.mmap(f.fileno(), 480*320*2)
    print('Framebuffer accessible, size:', len(mm))
"
```

### Touch Testing
```bash
# Test touch input
python3 -c "
import evdev
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
touch = next((d for d in devices if 'touch' in d.name.lower()), None)
if touch:
    print('Touch device found:', touch.name)
    for event in touch.read_loop():
        print(event)
        break
else:
    print('No touch device found')
"
```

### DFPlayer Testing
```bash
# Test serial communication
python3 -c "
import serial
try:
    ser = serial.Serial('/dev/serial0', 9600, timeout=1)
    print('UART0 accessible')
    ser.close()
except Exception as e:
    print('UART0 error:', e)
"
```

## Performance Considerations

### Memory Constraints
- **RAM Limit:** 512MB total on Pi Zero 2 W
- **Application Target:** < 100MB memory usage
- **Image Caching:** LRU cache with size limits
- **PIL Optimization:** Use RGB565 conversion, avoid unnecessary copies

### CPU Constraints
- **Target Usage:** < 50% during normal operation
- **Frame Rate:** 30 FPS target
- **Touch Latency:** < 100ms response time
- **Profiling:** Use cProfile for performance analysis

### Power Management
- **Display Backlight:** Software controllable
- **Touch Polling:** Event-driven, not continuous
- **Audio Playback:** Hardware decoding (DFPlayer)
- **Idle States:** Implement sleep modes

## Troubleshooting Hardware Issues

### Display Problems
**Blank Screen:**
- Check SPI enablement
- Verify cable connections
- Test with different display

**Corrupted Display:**
- Check RGB565 format support
- Verify framebuffer permissions
- Test direct memory writes

### Touch Problems
**No Response:**
- Check device detection (`ls /dev/input/event*`)
- Verify udev rules
- Test with `evtest`

**Incorrect Coordinates:**
- Run calibration procedure
- Check orientation settings
- Verify touch controller connections

### Audio Problems
**No Sound:**
- Check UART0 access
- Verify DFPlayer power
- Test serial communication

**Distorted Audio:**
- Check SD card format
- Verify file organization
- Test different audio files

## Migration Guides

### Waveshare 1.44" Display Migration
**From:** 1.28" ST7735 display
**To:** 1.44" ST7735 display (128x128 → 128x160)

**Changes Required:**
- Update screen dimensions in code
- Adjust button positions
- Recalibrate touch coordinates
- Update framebuffer mapping

### Touch Controller Variants
**Supported Controllers:**
- XPT2046 (most common)
- ADS7846 (compatible protocol)

**Configuration:**
- Same SPI interface
- Different calibration ranges possible
- Same 12-bit resolution

---

*This document consolidates information from: st7735_setup.md, touch_v2_setup.md, WAVESHARE_144_MIGRATION_PLAN.md, WAVESHARE_144_MIGRATION_PLAN_v2.md, button_reference.md, pi-tft-dfplayer-v0.2.md, and related hardware documentation.*</content>
<parameter name="filePath">docs/HARDWARE_INTEGRATION.md