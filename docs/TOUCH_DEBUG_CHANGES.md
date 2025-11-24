# Touch Input Debug Logging Implementation (Legacy)
Legacy touch debug notes. Future touch logging changes should be summarized in `docs/ai/TASK_LOG.md` and follow `docs/ai/PROJECT_GUIDE.md`.

## Completion Summary

All three tasks have been completed successfully. The application now has comprehensive logging throughout the touch event pipeline.

## Changes Made

### Task 1: Fixed Framebuffer Device Bug
**File:** `src/main_tft_v2.py` (line 55)

Changed default framebuffer device from `/dev/fb0` to `/dev/fb1` to match the TFT display:

```python
fb_device: str = "/dev/fb1",  # Was: "/dev/fb0"
```

### Task 2 & 3: Added Comprehensive Touch Event Logging

#### 1. Main Application Loop (`src/main_tft_v2.py`, lines 392-397)
Added periodic diagnostic logging every 100 frames:
- Current screen name
- Screen stack state
- Touch controller availability status

```python
if frame_count % 100 == 0:
    current_screen = self.screen_manager.current.name if self.screen_manager.current else "None"
    logger.info(f"[DIAG] Current screen: {current_screen}")
    logger.info(f"[DIAG] Screen stack: {self.screen_manager.stack()}")
    logger.info(f"[DIAG] Touch available: {self.touch is not None and getattr(self.touch, 'available', False)}")
```

#### 2. Touch Event Processing (`src/main_tft_v2.py`, lines 437-453)
Added logging in `_process_touch_events()`:
- Log when events are received from touch controller
- Log count of events
- Log raw event details (debug level)
- Log event type and coordinates
- Log UIEvent creation status
- Log routing to screen manager

```python
# Log when events are received
if events:
    logger.info(f"[TOUCH] Received {len(events)} touch events from controller")

for i, event in enumerate(events):
    # Log raw event details
    logger.debug(f"[TOUCH] Raw event {i}: {event.__dict__ if hasattr(event, '__dict__') else event}")
    logger.info(f"[TOUCH] Processing event {i}: type={getattr(event, 'type', 'UNKNOWN')}, "
               f"x={getattr(event, 'x', '?')}, y={getattr(event, 'y', '?')}")
```

#### 3. Touch-to-UI Event Conversion (`src/main_tft_v2.py`, lines 469-514)
Enhanced `_touch_to_ui_event()` with detailed logging:
- Log raw touch event attributes
- Log UIEvent type being created (tap/drag/swipe)
- Log coordinates and deltas
- Log unrecognized event types

```python
logger.debug(f"[CONVERT] Touch event type={event_type}, coords=({x}, {y}), raw=({raw_x}, {raw_y})")

if event_type == 'tap':
    logger.info(f"[CONVERT] Creating UIEvent TAP at ({x}, {y})")
elif event_type == 'drag':
    logger.info(f"[CONVERT] Creating UIEvent DRAG at ({x}, {y}), delta=({dx}, {dy})")
elif event_type == 'swipe':
    logger.info(f"[CONVERT] Creating UIEvent SWIPE direction={direction}, delta={delta}")
else:
    logger.warning(f"[CONVERT] Unrecognized event type: {event_type}")
```

#### 4. Screen Manager Event Routing (`src/ui/framework_v2/manager.py`, lines 77-86)
Added logging in `handle_event()`:
- Log which screen is receiving the event
- Log the event type
- Log the result from screen handler

```python
def handle_event(self, event: UIEvent) -> bool:
    screen = self.current
    if screen:
        logger.info(f"[MANAGER] Routing event {event.event_type} to screen: {screen.name}")
        result = screen.handle_event(event)
        logger.info(f"[MANAGER] Screen {screen.name} returned: {result}")
        return result
    else:
        logger.warning(f"[MANAGER] No current screen to handle event {event.event_type}")
    return False
```

#### 5. HomeScreen Event Handling (`src/ui/screens_v2/home.py`, lines 82-97)
Enhanced `handle_event()` with detailed button checking:
- Log event type and coordinates
- Log number of buttons being checked
- Log each button's rectangle and text (debug level)
- Log which button handled the event
- Log when no button matches

```python
def handle_event(self, event: UIEvent) -> bool:
    pos = event.payload.get("pos") if event.payload else None
    x, y = pos if pos else (None, None)

    logger.info(f"[HOME] Received event: type={event.event_type}, pos=({x}, {y})")
    logger.info(f"[HOME] Checking {len(self.buttons)} buttons")

    for i, button in enumerate(self.buttons):
        logger.debug(f"[HOME]   Button {i}: rect={button.rect}, text='{button.text}'")
        if button.handle_event(event):
            logger.info(f"[HOME]   Button {i} ('{button.text}') handled the event!")
            return True

    logger.info(f"[HOME] No button handled the event at ({x}, {y})")
    return False
```

## Log Prefixes for Easy Filtering

All logs are prefixed with tags for easy grep filtering:

- `[DIAG]` - Periodic diagnostic information
- `[TOUCH]` - Touch controller events
- `[CONVERT]` - Touch event to UIEvent conversion
- `[MANAGER]` - Screen manager routing
- `[HOME]` - HomeScreen event handling

## Testing Commands

```bash
# Start application with logging
sudo -E DFPLAYER_UI_FRAMEWORK=1 python3 src/main_tft_v2.py

# Filter logs by category
sudo journalctl -u dfplayer-fb -f | grep "\[TOUCH\]"
sudo journalctl -u dfplayer-fb -f | grep "\[MANAGER\]"
sudo journalctl -u dfplayer-fb -f | grep "\[HOME\]"

# View all touch-related logs
sudo journalctl -u dfplayer-fb -f | grep -E "\[TOUCH\]|\[CONVERT\]|\[MANAGER\]|\[HOME\]"
```

## Expected Log Flow

When a user taps the screen, you should see this sequence:

1. `[DIAG]` - Periodic diagnostics (every 100 frames)
2. `[TOUCH] Received N touch events from controller`
3. `[TOUCH] Processing event 0: type=tap, x=X, y=Y`
4. `[CONVERT] Touch event type=tap, coords=(X, Y)`
5. `[CONVERT] Creating UIEvent TAP at (X, Y)`
6. `[TOUCH] Created UIEvent: tap, routing to screen manager`
7. `[MANAGER] Routing event tap to screen: home`
8. `[HOME] Received event: type=tap, pos=(X, Y)`
9. `[HOME] Checking N buttons`
10. `[HOME] Button N ('Button Text') handled the event!` (if hit)
11. `[MANAGER] Screen home returned: True`

## Files Modified

1. `/Users/chase/pi-tft-dfplayer/src/main_tft_v2.py`
   - Line 55: Fixed framebuffer device default
   - Lines 392-397: Added diagnostic logging
   - Lines 437-453: Enhanced touch event processing logging
   - Lines 469-514: Enhanced event conversion logging

2. `/Users/chase/pi-tft-dfplayer/src/ui/framework_v2/manager.py`
   - Lines 1-10: Added logging import
   - Lines 77-86: Enhanced event routing logging

3. `/Users/chase/pi-tft-dfplayer/src/ui/screens_v2/home.py`
   - Lines 1-15: Added logging import
   - Lines 82-97: Enhanced button event handling logging

## Next Steps

With this comprehensive logging in place, you can now:

1. Run the application on the Raspberry Pi
2. Tap the screen and monitor the logs
3. Identify exactly where in the pipeline touch events are lost
4. Determine if the issue is:
   - Touch hardware not generating events
   - Events not being converted correctly
   - Coordinates not matching button regions
   - Button hit detection logic

The logging will pinpoint the exact failure point in the touch event pipeline.
