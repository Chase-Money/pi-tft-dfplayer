# Remaining Issues - Phase 1 Code Quality

## Testing Summary (2025-11-12)

### ✅ FIXED Issues
1. **Volume slider oscillation** - RESOLVED ✓
   - Volume now changes smoothly and audibly
   - No more back-and-forth jumping

2. **Track count query** - WORKING ✓
   - Now correctly reads 14 tracks from DFPlayer SD card
   - Query enhancement with dual-command approach successful

---

## 🔴 Outstanding Issues

### Issue 1: Intermittent Playback Failures (HIGH PRIORITY)

**Symptoms:**
- Some tracks play fine
- Some tracks don't play at all
- Some tracks attempt to play for ~1 second, then skip repeatedly in a loop
- Clicking track in listing or play button has same effect (no difference)
- User reports: "I can even get it to play sometimes if I click around enough"

**Current Behavior:**
```
Track 1:  ✓ Plays fine
Track 2:  ✗ Skips immediately
Track 3:  ⚠ Tries for 1s, skips, loops forever
Track 4:  ✓ Plays fine
...pattern varies
```

**Likely Root Causes:**
1. **DFPlayer serial communication timing issues**
   - Commands sent too quickly without waiting for ACK
   - No response validation after play commands
   - Rapid-fire commands when user clicks multiple times

2. **SD card file issues**
   - Corrupt MP3 files
   - Variable bitrate MP3 (DFPlayer struggles with VBR)
   - Files not in strict 0001.mp3, 0002.mp3 format
   - Non-standard sample rates

3. **DFPlayer state machine issues**
   - Module stuck in error state
   - Needs reset command (0x0C) before playing certain tracks
   - Busy flag not being checked

**Evidence from Code:**
```python
# src/dfplayer_fb_gui.py:429-434
def play_track_number(track_no):
    """Send DFPlayer command to play specific track number."""
    send(0x03, track_no >> 8, track_no & 0xFF)
    time.sleep(0.05)  # ONLY 50ms DELAY - may be too short!
    # NO ACK CHECKING - we don't know if it succeeded
```

**File Location:** `src/dfplayer_fb_gui.py:429-434`, `play_track_number()`

---

### Issue 2: No Auto-Advance (MEDIUM PRIORITY)

**Symptoms:**
- When a song finishes playing, playback stops
- Should automatically advance to next track
- User expects continuous playback through entire playlist

**Current Behavior:**
```
User plays Track 1 → Track 1 plays → Track 1 ends → Silence (stops)
Expected: Track 1 → Track 2 → Track 3 → ... → Track 14
```

**Root Cause:**
DFPlayer Mini can send "playback finished" notifications via serial, but:
1. We don't have a background thread reading serial responses
2. No event loop processing DFPlayer status messages
3. No automatic track advance logic implemented

**Evidence from Code:**
```python
# Main event loop only processes touch events
# src/dfplayer_fb_gui.py:1057-1140
while True:
    # Read touch events
    for evt in evdev_dev.read():
        # Process touch input
    # NO SERIAL READING HERE - we never check if track finished
```

**File Location:** `src/dfplayer_fb_gui.py:1057-1140`, main event loop

---

### Issue 3: UI Text Overlap - Volume Level Hidden (LOW PRIORITY)

**Symptoms:**
- Volume level number (0-30) is hidden behind track listing panel
- User cannot see current volume value
- Visual feedback missing

**Expected Layout:**
```
Left Panel (X=20-220):
- Play button (20, 20)
- Stop button (20, 110)
- Prev/Next (20, 180)
- Volume slider (20, 260)
- Volume text "Vol: 18" ← SHOULD BE VISIBLE

Right Panel (X=240-460):
- Track listing panel ← OVERLAPPING LEFT PANEL TEXT
```

**Root Cause:**
Z-order rendering issue. Track listing panel is drawn **after** volume text, covering it.

**Evidence from Code:**
```python
# src/dfplayer_fb_gui.py:649-756 (draw_ui function)
# Drawing order:
1. Draw buttons (line ~670)
2. Draw volume bar (line ~690)
3. Draw volume text (line ~700) ← DRAWN FIRST
4. Draw track listing panel (line ~720) ← DRAWN LATER, COVERS TEXT
```

**File Location:** `src/dfplayer_fb_gui.py:649-756`, `draw_ui()` rendering order

---

### Issue 4: UI Text Overlap - Track Info Hidden (LOW PRIORITY)

**Symptoms:**
- Track metadata (title, artist) should appear above track listing
- Currently hidden behind track listing panel
- User cannot see "Now Playing" information

**Expected Behavior:**
```
Right Panel:
- Track info area (X=260, Y=230-302) ← SHOULD BE ON TOP
- Track listing (X=240, Y=50-250) ← COVERING TRACK INFO
```

**Root Cause:**
Same as Issue 3 - Z-order rendering. Track listing panel drawn after track info, obscuring it.

**File Location:** `src/dfplayer_fb_gui.py:649-756`, `draw_ui()` rendering order

---

## 📋 Fix Plan

### Phase 2A: Playback Reliability (HIGH PRIORITY)

**Goal:** Eliminate intermittent playback failures

#### Task 2A.1: Implement Response Validation
**File:** `src/dfplayer_fb_gui.py:429-434`
**Changes:**
```python
def play_track_number(track_no):
    """Send DFPlayer command to play specific track number with validation."""
    # Clear any pending responses
    if ser and ser.in_waiting:
        ser.read(ser.in_waiting)

    # Send play command
    send(0x03, track_no >> 8, track_no & 0xFF)

    # Wait for ACK (increased from 50ms to 200ms)
    time.sleep(0.2)

    # Read and validate response
    response = read_dfplayer_response(timeout=0.3)
    if response:
        if response[3] == 0x40:  # Error response
            error_code = response[6]
            logger.error(f"DFPlayer error playing track {track_no}: code {error_code:02x}")
            return False
        elif response[3] == 0x3D:  # Playback finished (immediate fail)
            logger.warning(f"Track {track_no} finished immediately (file issue?)")
            return False
        else:
            logger.info(f"Track {track_no} started successfully")
            return True
    else:
        logger.warning(f"No ACK received for track {track_no}")
        return False
```

**Testing:** Try playing each track 1-14, log which succeed vs fail with error codes.

#### Task 2A.2: Add DFPlayer Reset on Errors
**File:** `src/dfplayer_fb_gui.py` (new function)
**Changes:**
```python
def reset_dfplayer():
    """Reset DFPlayer module to clear error states."""
    logger.info("Resetting DFPlayer module...")
    send(0x0C, 0, 0)  # Reset command
    time.sleep(0.5)   # Give time to reset

    # Re-initialize: set volume, select source
    send(0x06, 0, 18)  # Set volume to 18
    time.sleep(0.1)
    send(0x09, 0, 2)   # Select TF card as source
    time.sleep(0.1)
```

Call this function:
- On startup (after serial init)
- After 3 consecutive playback failures
- When user long-presses Stop button

#### Task 2A.3: Prevent Rapid-Fire Commands
**File:** `src/dfplayer_fb_gui.py:1057-1140`
**Changes:**
```python
# Add rate limiting for play commands
last_play_cmd = 0
MIN_PLAY_INTERVAL = 0.5  # Minimum 500ms between play commands

def handle_tap(x, y):
    global last_play_cmd

    # ... existing button detection code ...

    if key == "play":
        now = time.time()
        if now - last_play_cmd < MIN_PLAY_INTERVAL:
            logger.debug("Ignoring rapid play command")
            return
        last_play_cmd = now
        # ... existing play logic ...
```

**Testing:** Rapidly click play button - should ignore rapid clicks.

#### Task 2A.4: Add SD Card Diagnostic Tool
**File:** `scripts/check_dfplayer_sd.sh` (new script)
**Purpose:** Help user verify SD card file integrity without removing card

```bash
#!/bin/bash
# Query DFPlayer for each track individually
# Log which tracks respond vs fail
# Generate report for user

echo "Testing DFPlayer SD card tracks..."
for i in {1..14}; do
    echo "Testing track $i..."
    # Send play command, check for ACK
    # Log result
done
```

---

### Phase 2B: Auto-Advance Playback (MEDIUM PRIORITY)

**Goal:** Automatically play next track when current track finishes

#### Task 2B.1: Background Serial Reader Thread
**File:** `src/dfplayer_fb_gui.py` (new thread)
**Changes:**
```python
import threading
import queue

# Global queue for DFPlayer events
dfplayer_events = queue.Queue()

def dfplayer_listener_thread():
    """Background thread to read DFPlayer status messages."""
    global ser, dfplayer_events

    while True:
        if ser and ser.is_open:
            try:
                if ser.in_waiting >= 10:
                    response = read_dfplayer_response(timeout=0.1)
                    if response:
                        cmd = response[3]

                        # Track finished playback
                        if cmd == 0x3D:
                            dfplayer_events.put({"event": "track_finished"})
                            logger.info("Track finished, auto-advancing...")

                        # Track started
                        elif cmd == 0x3E:
                            track_num = (response[5] << 8) | response[6]
                            dfplayer_events.put({"event": "track_started", "track": track_num})

                        # Error occurred
                        elif cmd == 0x40:
                            error_code = response[6]
                            dfplayer_events.put({"event": "error", "code": error_code})

            except Exception as e:
                logger.error(f"Serial reader error: {e}")

        time.sleep(0.05)  # Check every 50ms

# Start thread on app init
listener = threading.Thread(target=dfplayer_listener_thread, daemon=True)
listener.start()
```

#### Task 2B.2: Process Events in Main Loop
**File:** `src/dfplayer_fb_gui.py:1057-1140`
**Changes:**
```python
while True:
    # Process DFPlayer events
    try:
        while not dfplayer_events.empty():
            event = dfplayer_events.get_nowait()

            if event["event"] == "track_finished":
                # Auto-advance to next track
                advance_track(1)
                selected = get_selected_track()
                if selected:
                    play_track_number(selected["number"])
                    draw_ui()

            elif event["event"] == "error":
                logger.error(f"DFPlayer error: {event['code']}")
                # Maybe show error on UI

    except queue.Empty:
        pass

    # ... existing touch event processing ...
```

**Testing:** Play track 1, wait for it to finish, verify track 2 starts automatically.

---

### Phase 2C: UI Text Overlap Fixes (LOW PRIORITY)

**Goal:** Make volume level and track info visible

#### Task 2C.1: Adjust Volume Text Position
**File:** `src/dfplayer_fb_gui.py:~700`
**Changes:**
```python
# Current (hidden behind track panel):
# Volume text drawn at Y=290 or similar

# Fix: Move volume text ABOVE volume slider
vol_text_y = VOLBAR_RECT[1] - 20  # 20px above slider
d.text((20, vol_text_y), f"Vol: {vol}", font=fnt14, fill=(200, 200, 200))

# Alternative: Move to RIGHT of volume slider
vol_text_x = VOLBAR_RECT[0] + VOLBAR_RECT[2] + 10  # 10px right of slider end
d.text((vol_text_x, VOLBAR_RECT[1] + 5), f"Vol: {vol}", font=fnt14, fill=(200, 200, 200))
```

#### Task 2C.2: Adjust Track Info Position
**File:** `src/dfplayer_fb_gui.py:~730`
**Changes:**
```python
# Current track info region: X=260, Y=230-302
# Track listing panel: X=240, Y=50-250

# Option 1: Move track info BELOW track listing
track_info_y = 260  # Below listing, above buttons

# Option 2: Draw track info AFTER track listing (on top in Z-order)
# Reorder draw_ui() calls:
#   1. Draw track listing panel first
#   2. Draw track info second (on top)

# Option 3: Make track listing panel narrower to not overlap
track_panel_x = 260  # Start at X=260 instead of X=240
```

#### Task 2C.3: Add Z-Order Comments
**File:** `src/dfplayer_fb_gui.py:649-756`
**Changes:**
```python
def draw_ui():
    """Render UI to PIL image.

    Z-order (bottom to top):
    1. Background
    2. Buttons (left panel)
    3. Volume slider (left panel)
    4. Track listing panel (right panel) ← DRAW FIRST
    5. Track info / metadata (right panel) ← DRAW LAST (ON TOP)
    6. Volume text (left panel) ← DRAW LAST (ON TOP)
    """
    # ... implementation with clear ordering ...
```

---

## 🎯 Implementation Priority

### Immediate (Phase 2A - Next Session):
1. ✅ Task 2A.1: Response validation in `play_track_number()`
2. ✅ Task 2A.2: DFPlayer reset function
3. ✅ Task 2A.3: Rapid-fire command prevention

**Estimated Time:** 1-2 hours
**Testing Required:** Yes - test all 14 tracks, log success/failure patterns

### Soon (Phase 2B - After 2A Tested):
4. ✅ Task 2B.1: Background serial reader thread
5. ✅ Task 2B.2: Auto-advance event processing

**Estimated Time:** 1-2 hours
**Testing Required:** Yes - verify smooth track-to-track playback

### Later (Phase 2C - Polish):
6. ✅ Task 2C.1: Volume text positioning
7. ✅ Task 2C.2: Track info positioning
8. ✅ Task 2C.3: Z-order documentation

**Estimated Time:** 30 minutes
**Testing Required:** Visual inspection only

---

## 📝 Notes

### DFPlayer Serial Protocol - Status Messages

The DFPlayer Mini sends unsolicited status messages:

| Response | Hex  | Description |
|----------|------|-------------|
| Track Started | 0x3E | Sent when playback begins |
| Track Finished | 0x3D | Sent when playback completes |
| Error | 0x40 | Error occurred (with error code) |
| Current Track | 0x4C | Response to query (we already use this) |

**Format:**
```
0x7E FF 06 [CMD] 00 [P1] [P2] [CS_H] [CS_L] EF

Track finished:
0x7E FF 06 3D 00 00 01 [CS] [CS] EF
```

### User Reported Behavior Pattern

> "Some I can even get to play sometimes if I click around enough. But usually it just tries for like one second and skips it."

This suggests:
- Commands ARE being received by DFPlayer
- Files likely exist (otherwise would fail immediately always)
- Issue is timing/state-related, not missing files
- Multiple rapid commands might be interfering with each other

### SD Card File Verification

User should verify SD card structure (optional, for diagnostics):
```bash
# Remove DFPlayer SD card
# Insert into computer
# Check structure:
/mp3/
  ├── 0001.mp3
  ├── 0002.mp3
  ├── 0003.mp3
  └── ... (up to 0014.mp3)

# Verify no gaps, all files present
# Check file sizes (corrupt files are often 0 bytes or tiny)
# Verify MP3 format (not WAV with .mp3 extension)
```

---

## 🏁 Summary

**Current State:**
- ✅ Volume slider working perfectly
- ✅ DFPlayer query working (14 tracks detected)
- 🔴 Intermittent playback failures (needs investigation)
- 🔴 No auto-advance (needs implementation)
- 🟡 Minor UI text overlap (easy fix)

**Next Steps:**
1. Implement Phase 2A (playback reliability) - HIGH PRIORITY
2. Test on hardware, gather playback logs
3. Based on results, implement Phase 2B (auto-advance)
4. Polish with Phase 2C (UI fixes)

**Confidence Levels:**
- Phase 2A fixes: 85% confidence (need hardware testing to confirm root cause)
- Phase 2B implementation: 95% confidence (standard serial reader pattern)
- Phase 2C fixes: 100% confidence (simple Z-order/positioning changes)
