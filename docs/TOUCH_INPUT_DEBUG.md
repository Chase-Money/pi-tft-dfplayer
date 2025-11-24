# Touch Input Debugging Notes (Legacy)
Legacy touch debugging log. For new investigations, record outcomes in `docs/ai/TASK_LOG.md` and align with `docs/ai/PROJECT_GUIDE.md`.

**Status:** Touch controller initializes successfully but button clicks have no effect
**Date:** 2025-11-20
**Branch:** feature/framework-migration

## Current Behavior

✅ **Working:**
- Touch controller initialization succeeds
- Touch orientation configured: `swap=True, flip_x=True, flip_y=True`
- Touch device detected at `/dev/input/touchscreen`

❌ **Not Working:**
- Button clicks don't trigger any actions
- No visual feedback when tapping buttons
- No logging of touch events in application logs

## Investigation Strategy

### 1. Verify Touch Hardware
Test that the touch device is generating events:
```bash
sudo evtest /dev/input/touchscreen
# Tap the screen - should see ABS_X, ABS_Y, BTN_TOUCH events
```

### 2. Add Logging to Event Pipeline

**src/main_tft_v2.py:_process_touch_events()** (around line 430)

Add logging at each stage:
```python
def _process_touch_events(self) -> None:
    if not self.touch:
        return

    try:
        events = self.touch.get_events(timeout=0)
        
        # ADD THIS:
        if events:
            logger.info(f"Got {len(events)} touch events")
        
        for event in events:
            # ADD THIS:
            logger.info(f"Processing event: type={event.event_type}, x={event.x}, y={event.y}")
            
            ui_event = UIEvent(
                event_type=event.event_type,
                x=event.x,
                y=event.y,
                raw_x=event.raw_x,
                raw_y=event.raw_y
            )
            
            # ADD THIS:
            logger.info(f"Created UIEvent, routing to screen manager")
            
            self.screen_manager.handle_event(ui_event)
```

### 3. Check Button Hit Detection

**src/ui/screens_v2/home.py:handle_event()** (line 83)

Add logging to see if events reach the buttons:
```python
def handle_event(self, event: UIEvent) -> bool:
    logger.info(f"HomeScreen received event at ({event.x}, {event.y})")
    for i, button in enumerate(self.buttons):
        logger.info(f"  Checking button {i}: rect={button.rect}")
        if button.handle_event(event):
            logger.info(f"  Button {i} handled the event!")
            return True
    logger.info("  No button handled the event")
    return False
```

### 4. Verify Button Rectangles

Check that button positions are correct for the screen resolution:
```python
# In home.py render() method, log button rectangles:
for i, button in enumerate(self.buttons):
    logger.debug(f"Button {i}: {button.rect} - {button.text}")
```

### 5. Check Screen Manager Event Routing

**src/ui/framework_v2/manager.py:handle_event()**

Ensure events are reaching the current screen:
```python
def handle_event(self, event: UIEvent) -> bool:
    if not self._stack:
        return False
    
    current_screen = self._stack[-1]
    # ADD THIS:
    logger.info(f"Routing event to screen: {current_screen.name}")
    
    return current_screen.handle_event(event)
```

## Possible Root Causes

1. **Touch coordinates not transformed correctly**
   - Raw touch coordinates may not match button pixel coordinates
   - Orientation/calibration settings might be inverting coordinates

2. **Event type mismatch**
   - Touch controller might be generating PRESS/RELEASE events
   - Buttons might be expecting DOWN/UP events
   - Check `src/ui/framework_v2/events.py` for event type definitions

3. **Touch events not being read**
   - `self.touch.get_events()` might return empty list
   - Non-blocking read (timeout=0) might be too fast
   - Try increasing timeout to 10ms: `get_events(timeout=0.01)`

4. **Screen manager not initialized properly**
   - Current screen might not be "home"
   - Stack might be empty
   - Check `self.screen_manager.current_screen` property

## Quick Test

Add this to the main loop in `src/main_tft_v2.py:run()`:
```python
while self.running:
    # ADD THIS before touch processing:
    if frame_count % 100 == 0:
        logger.info(f"Current screen: {self.screen_manager.current_screen}")
        logger.info(f"Screen stack: {[s.name for s in self.screen_manager._stack]}")
    
    if self.touch:
        self._process_touch_events()
```

## Testing Commands

```bash
# Start app with debug logging
ssh kiosk "cd ~/projects/pi-tft-dfplayer && sudo -E DFPLAYER_UI_FRAMEWORK=1 python3 src/main_tft_v2.py > /tmp/touch_debug.log 2>&1 &"

# Monitor logs for touch events
ssh kiosk "tail -f /tmp/touch_debug.log | grep -E 'touch|event|button|screen'"

# Test touch device directly
ssh kiosk "sudo evtest /dev/input/touchscreen"
```

## Next Steps After Investigation

1. If events aren't being generated → Hardware/driver issue
2. If events generated but not received → Check `get_events()` implementation
3. If events received but not reaching buttons → Check coordinate transformation
4. If events reach buttons but don't trigger → Check button event handlers

## Related Files

- `src/main_tft_v2.py` - Main app, event processing loop
- `src/hardware/touch_controller.py` - Touch device abstraction
- `src/ui/framework_v2/manager.py` - Screen manager, event routing
- `src/ui/framework_v2/widgets.py` - ButtonWidget, event handling
- `src/ui/screens_v2/home.py` - Home screen, button definitions
- `src/ui/framework_v2/events.py` - UIEvent definitions
