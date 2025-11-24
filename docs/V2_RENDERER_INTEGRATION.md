# V2 Renderer Integration Guide

## Overview

The V2 renderer system integrates the modular UI framework with the Raspberry Pi framebuffer, providing a complete rendering pipeline for the DFPlayer TFT application.

## Architecture

### Components

1. **FramebufferRendererV2** (`src/ui/renderer_v2/renderer.py`)
   - Double-buffered PIL-based rendering
   - Automatic framebuffer size detection
   - Font management and caching
   - Integration with ScreenManagerV2

2. **TouchController** (`src/hardware/touch_controller.py`)
   - Event-based touch handling
   - Gesture detection (tap, drag, swipe)
   - Calibration and orientation support

3. **Main Application** (`src/main_tft_v2.py`)
   - Complete integration of all subsystems
   - Event loop with FPS tracking
   - Resource management and cleanup

## Quick Start

### Running on Hardware

```bash
# Navigate to repository
cd /home/pi/pi-tft-dfplayer

# Run the V2 application with default settings
sudo PYTHONPATH=$(pwd):$(pwd)/src python3 src/main_tft_v2.py

# Or specify custom framebuffer/touch device
sudo PYTHONPATH=$(pwd):$(pwd)/src python3 src/main_tft_v2.py --fb /dev/fb1 --touch /dev/input/touchscreen
```

### Command-Line Options

- `--fb DEVICE`: Framebuffer device path (default: `/dev/fb0`)
- `--touch DEVICE`: Touch device path (default: auto-detect)

## Rendering Pipeline

### 1. Initialization

```python
# Create framebuffer
framebuffer = Framebuffer(device="/dev/fb0")

# Create screen manager with services
screen_manager = ScreenManagerV2(services={
    "state": app_state,
    "backend": dfplayer_backend,
    "app": app
})

# Create renderer
renderer = FramebufferRendererV2(
    framebuffer=framebuffer,
    screen_manager=screen_manager
)
```

### 2. Main Loop

```python
while running:
    # Process touch events
    events = touch_controller.get_events(timeout=0)
    for event in events:
        ui_event = convert_to_ui_event(event)
        screen_manager.handle_event(ui_event)

    # Render and present
    renderer.render_and_present()

    # Frame rate control
    time.sleep(0.033)  # ~30 FPS
```

## Touch Event Mapping

### TouchController Events

The `TouchController` generates the following event types:

- **press**: Touch down
- **release**: Touch up
- **tap**: Quick press and release (< 300ms, < 10px movement)
- **drag**: Press, move, release (< 50px)
- **swipe**: Fast movement (>= 50px) with direction

### UIEvent Conversion

Touch events are converted to `UIEvent` objects for the screen manager:

```python
TouchEvent(type='tap', x=100, y=50)
  → UIEvent('tap', payload={'x': 100, 'y': 50})

TouchEvent(type='swipe', direction='up', delta=-50)
  → UIEvent('swipe', payload={'direction': 'up', 'delta': -50})
```

## Screen Development

### Creating a New Screen

```python
from ui.framework_v2.manager import ScreenView
from ui.framework_v2.widgets import ButtonWidget
from ui.framework_v2.events import UIEvent

class MyScreen(ScreenView):
    name = "my_screen"

    def __init__(self, manager, services=None):
        super().__init__(manager, services)
        self.buttons = []

    def on_enter(self, **kwargs):
        """Called when screen becomes active."""
        # Create UI widgets
        self.buttons = [
            ButtonWidget(
                rect=(10, 10, 200, 60),
                label="Click Me",
                on_press=self.handle_click
            )
        ]

    def render(self, context: dict) -> None:
        """Render the screen."""
        image = context["image"]
        draw = context["draw"]
        fonts = context["fonts"]

        # Clear background
        draw.rectangle(
            (0, 0, image.width, image.height),
            fill=(12, 16, 24)
        )

        # Draw widgets
        for button in self.buttons:
            button.draw(draw, fonts["medium"])

    def handle_event(self, event: UIEvent) -> bool:
        """Handle touch/UI events."""
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False

    def handle_click(self):
        """Button click handler."""
        print("Button clicked!")
```

### Registering the Screen

```python
screen_manager.register("my_screen", MyScreen)
screen_manager.push("my_screen")
```

## Font Management

The renderer automatically loads and caches fonts in common sizes:

- **small**: 14px
- **medium**: 18px
- **large**: 24px
- **xlarge**: 32px

Access fonts in your screen's `render()` method:

```python
def render(self, context: dict) -> None:
    fonts = context["fonts"]
    small_font = fonts["small"]
    medium_font = fonts["medium"]
    # ...
```

## Performance Optimization

### Target Frame Rate

The application targets ~30 FPS (0.033s per frame) for smooth rendering without excessive CPU usage.

### Rendering Best Practices

1. **Minimize Redraws**: Only update widgets that have changed
2. **Cache Images**: Pre-load artwork and cache in memory
3. **Efficient Drawing**: Use simple shapes when possible
4. **Font Reuse**: Use pre-cached fonts from the renderer

### FPS Monitoring

The main loop logs FPS every 5 seconds:

```
INFO - FPS: 29.8
```

## Hardware Compatibility

### Tested Configurations

- **Display**: ILI9486 SPI TFT (480x320) on `/dev/fb0` or `/dev/fb1`
- **Touch**: XPT2046/ADS7846 resistive touch via evdev
- **Platform**: Raspberry Pi Zero 2 W, Pi 3, Pi 4

### Display Detection

The renderer automatically detects framebuffer size from sysfs:

```
/sys/class/graphics/fb0/virtual_size
```

Fallback: 480x320 if detection fails

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

#### "Failed to initialize framebuffer"
- Check device exists: `ls /dev/fb0`
- Verify permissions: `sudo chmod 666 /dev/fb0`
- Check framebuffer is enabled in `/boot/config.txt`

#### "Failed to initialize touch controller"
- Check device: `ls /dev/input/event*`
- Install evdev: `pip3 install evdev`
- Add user to input group: `sudo usermod -a -G input $USER`

#### "No screen rendering"
- Verify screen is registered: Check `screen_manager.register()` calls
- Confirm initial screen is pushed: `screen_manager.push("home")`
- Check render method is called: Add debug logging

#### "Touch not responding"
- Verify touch events: `evtest /dev/input/touchscreen`
- Check calibration: May need touch calibration
- Ensure event loop processes touch: Check `_process_touch_events()`

## Migration from V1

### Key Differences

| V1 (dfplayer_fb_gui.py) | V2 (Renderer + Framework) |
|------------------------|---------------------------|
| Single monolithic file | Modular architecture |
| Direct framebuffer writes | FramebufferRendererV2 |
| Inline UI rendering | Screen classes + widgets |
| No screen navigation | ScreenManagerV2 stack |
| Manual touch processing | TouchController events |

### Migration Steps

1. **Extract UI Logic**: Convert UI sections to Screen classes
2. **Use Widgets**: Replace custom drawing with framework widgets
3. **Event Handlers**: Convert touch logic to `handle_event()` methods
4. **State Management**: Use AppState instead of global variables
5. **Backend Integration**: Use DFPlayerBackend instead of direct serial

## API Reference

### FramebufferRendererV2

```python
class FramebufferRendererV2:
    def __init__(framebuffer, screen_manager=None, default_font_path=...)
    def render() -> None  # Render current screen to backbuffer
    def present() -> None  # Push backbuffer to framebuffer
    def render_and_present() -> None  # Convenience method
    def get_font(name: str) -> ImageFont  # Get cached font
    def clear(color=(0,0,0)) -> None  # Clear backbuffer
    def close() -> None  # Cleanup
```

### TouchController

```python
class TouchController:
    def __init__(device=None)
    def get_events(timeout=0.0) -> List[TouchEvent]
    def set_calibration(min_x, max_x, min_y, max_y) -> None
    def set_orientation(swap_xy, flip_x, flip_y) -> None
    def close() -> None
```

### TouchEvent

```python
@dataclass
class TouchEvent:
    type: str  # 'tap', 'drag', 'swipe', 'press', 'release'
    x: int
    y: int
    dx: int = 0
    dy: int = 0
    direction: Optional[str] = None
    timestamp: float = 0.0
```

## Examples

See `src/ui/screens_v2/` for reference implementations:
- `home.py`: Simple navigation screen
- `track_browser.py`: Scrollable list with selection
- `now_playing.py`: Playback controls with artwork

## Support

For issues or questions:
- Check logs: `journalctl -u dfplayer-fb -f`
- Review documentation: `docs/`
- Open an issue on GitHub
