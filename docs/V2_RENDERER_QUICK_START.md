# V2 Renderer Quick Start Guide

## What's New

The V2 renderer system provides a complete, modular UI framework for the DFPlayer TFT application.

### New Files Created

1. **`src/ui/renderer_v2/renderer.py`** - FramebufferRendererV2 class
2. **`src/ui/renderer_v2/__init__.py`** - Module init
3. **`src/hardware/touch_controller.py`** - TouchController with event-based input
4. **`src/main_tft_v2.py`** - Complete TFT touch application

### Fixed Files

1. **`src/main_touch_v2.py`** - Fixed module import errors

## Testing on Hardware

### Step 1: Pull Latest Code

```bash
cd /home/pi/pi-tft-dfplayer
git pull origin feature/framework-migration
```

### Step 2: Install Dependencies

```bash
sudo pip3 install pillow pyserial
```

On Raspberry Pi with evdev support:
```bash
sudo apt-get install python3-evdev
```

### Step 3: Test Rendering

```bash
# Run the new V2 application
sudo PYTHONPATH=$(pwd):$(pwd)/src python3 src/main_tft_v2.py
```

Expected behavior:
- Display initializes and clears to black
- Home screen appears with navigation buttons
- Touch input is detected
- FPS logs appear every 5 seconds

### Step 4: Test Touch Input

Touch the screen and verify:
- Tap detection works
- Buttons respond to touches
- Screen navigation functions
- No flickering or tearing

### Step 5: Test Backend Integration

Verify DFPlayer communication:
- Backend initializes without errors
- Track playback commands work
- Volume control responds
- Track navigation functions

## Troubleshooting

### Module Import Errors

If you see `ModuleNotFoundError`:

```bash
# Make sure PYTHONPATH includes both project root and src
export PYTHONPATH=$(pwd):$(pwd)/src
sudo -E python3 src/main_tft_v2.py
```

### Framebuffer Permission Denied

```bash
sudo chmod 666 /dev/fb0
# Or run with sudo
sudo python3 src/main_tft_v2.py
```

### Touch Device Not Found

```bash
# List input devices
ls -la /dev/input/

# Test touch device
sudo evtest /dev/input/touchscreen

# If device not found, check udev rules
cat /etc/udev/rules.d/95-touchscreen.rules
```

### No Display Output

Check framebuffer:
```bash
# Verify framebuffer exists
ls -la /dev/fb*

# Check framebuffer info
fbset -i

# Test with raw data
sudo dd if=/dev/zero of=/dev/fb0
```

### Import Errors for V2 Modules

If you see errors like "No module named 'src.backends.dfplayer_backend_v2'":
- This has been fixed in `main_touch_v2.py`
- Use `main_tft_v2.py` instead, which has correct imports

## Verification Checklist

- [ ] Application starts without errors
- [ ] Framebuffer initializes (width x height logged)
- [ ] Touch controller initializes
- [ ] DFPlayer backend connects
- [ ] Home screen renders
- [ ] Touch input detected
- [ ] Buttons respond to taps
- [ ] Screen navigation works (push/pop)
- [ ] FPS is stable (~30 FPS)
- [ ] No memory leaks (check with `top`)
- [ ] Clean shutdown with Ctrl+C

## Performance Benchmarks

Expected performance on Raspberry Pi Zero 2 W:
- **FPS**: 25-30 FPS
- **CPU Usage**: 20-40%
- **Memory**: ~50 MB
- **Touch Latency**: < 50ms

## Comparing V1 vs V2

| Feature | V1 (dfplayer_fb_gui.py) | V2 (main_tft_v2.py) |
|---------|------------------------|---------------------|
| Architecture | Monolithic | Modular |
| Lines of Code | ~800 | ~400 (main) + framework |
| Screen Navigation | Manual | ScreenManagerV2 |
| Rendering | Direct PIL | FramebufferRendererV2 |
| Touch Processing | Inline | TouchController |
| Widget System | Custom drawing | Reusable widgets |
| Testing | Limited | Full test suite |

## Next Steps

### For Development

1. Create custom screens in `src/ui/screens_v2/`
2. Add new widgets in `src/ui/framework_v2/widgets.py`
3. Extend TouchController for gestures
4. Add calibration screen

### For Production

1. Test all hardware configurations
2. Verify track catalog loading
3. Test metadata and artwork
4. Configure systemd service
5. Set up auto-start on boot

## Example: Creating a Settings Screen

```python
# src/ui/screens_v2/settings.py
from ui.framework_v2.manager import ScreenView
from ui.framework_v2.widgets import ButtonWidget

class SettingsScreen(ScreenView):
    name = "settings"

    def on_enter(self, **kwargs):
        self.buttons = [
            ButtonWidget((10, 10, 200, 60), "Calibrate Touch",
                        lambda: self.manager.push("calibration")),
            ButtonWidget((10, 80, 200, 60), "Back",
                        lambda: self.manager.pop())
        ]

    def render(self, context):
        draw = context["draw"]
        draw.rectangle((0, 0, 480, 320), fill=(12, 16, 24))
        for btn in self.buttons:
            btn.draw(draw, context["fonts"]["medium"])

    def handle_event(self, event):
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        return False

# Register in main_tft_v2.py
screen_manager.register("settings", SettingsScreen)
```

## Hardware Testing Matrix

| Hardware | Status | Notes |
|----------|--------|-------|
| Pi Zero 2 W + ILI9486 | ✅ Target | Primary development platform |
| Pi 3 B+ + ILI9486 | ⚠️ Untested | Should work |
| Pi 4 + ILI9486 | ⚠️ Untested | Should work |
| Waveshare 1.44" HAT | ⚠️ Separate | Use app_waveshare.py |

## Support

If you encounter issues:
1. Check logs for error messages
2. Verify all dependencies installed
3. Test hardware with simple framebuffer writes
4. Review documentation in `docs/`
5. Create an issue with logs and hardware details

## Success Indicators

You know it's working when:
- ✅ Screen shows UI elements (not blank)
- ✅ Touch causes visual feedback
- ✅ Buttons change appearance on tap
- ✅ Screen transitions are smooth
- ✅ FPS logs show stable frame rate
- ✅ No error messages in logs
- ✅ Ctrl+C cleanly shuts down

## Congratulations!

If all tests pass, you now have a fully functional V2 renderer system integrated with the DFPlayer TFT application. The modular architecture makes it easy to add new screens, widgets, and features.

Happy coding! 🎵
