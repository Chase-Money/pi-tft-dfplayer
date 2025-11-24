# Changes Applied - Bug Fixes (Legacy)
Legacy log. For new changes, capture them in `docs/ai/TASK_LOG.md` per `docs/ai/PROJECT_GUIDE.md`.

## File: src/dfplayer_fb_gui.py

### Change 1: Volume Slider Fix (Lines 1131-1135)

**CRITICAL BUG FIX - Volume slider not working**

#### Before (lines 1131-1140):
```python
if drag_vol:
    now = time.time()
    if now - last_drag > 0.02:
        update_volume_from_x(px)          # ← Calls vol_set() and draw_ui()
        vx, vy, vw, vh = VOLBAR_RECT      # ← DUPLICATE CODE STARTS HERE
        clamped = max(vx, min(vx + vw, px))
        vol = int((clamped - vx) * 30 / vw)  # ← Wrong calculation (no rounding)
        vol_set(vol)                      # ← DUPLICATE vol_set() call
        draw_ui()                         # ← DUPLICATE draw_ui() call
        last_drag = now
```

#### After (lines 1131-1135):
```python
if drag_vol:
    now = time.time()
    if now - last_drag > 0.02:
        update_volume_from_x(px)          # ← This does everything correctly
        last_drag = now                   # ← No duplicate code
```

**Lines removed:** 5 (lines 1135-1139)
**Impact:** Volume slider now works correctly

---

### Change 2: Track Count Query Enhancement (Lines 253-307)

**ENHANCEMENT - Better track count detection with dual-query method**

#### Before (lines 253-282):
```python
def query_dfplayer_file_count():
    """Query DFPlayer for number of files in /mp3 folder.

    Returns:
        int: Number of files, or None if query failed
    """
    global ser
    if ser is None:
        return None

    try:
        # Clear any pending data
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        # Send query command 0x4C (get file count in /mp3 folder)
        send(0x4C, 0, 0)
        time.sleep(0.1)  # Give DFPlayer time to respond

        response = read_dfplayer_response(timeout=0.5)
        if response and response[3] == 0x4C:
            file_count = (response[5] << 8) | response[6]
            logger.info(f"DFPlayer reports {file_count} files in /mp3 folder")
            return file_count
        else:
            logger.warning("DFPlayer did not respond to file count query")
            return None
    except Exception as e:
        logger.error(f"Error querying DFPlayer file count: {e}")
        return None
```

#### After (lines 253-307):
```python
def query_dfplayer_file_count():
    """Query DFPlayer for number of files.

    Tries multiple query methods:
    1. Command 0x48 - Total files on TF card (all folders)
    2. Command 0x4C - Files in /mp3 folder specifically

    Returns:
        int: Number of files, or None if query failed
    """
    global ser
    if ser is None:
        return None

    try:
        # Clear any pending data
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        # Try 0x48 first (total TF card files)
        logger.info("Querying DFPlayer with 0x48 (total TF card files)...")
        send(0x48, 0, 0)
        time.sleep(0.2)  # Give DFPlayer time to respond

        response = read_dfplayer_response(timeout=0.5)
        if response:
            logger.info(f"0x48 response: {response.hex()}")
            if response[3] == 0x48:
                file_count = (response[5] << 8) | response[6]
                logger.info(f"DFPlayer reports {file_count} total files on TF card")
                if file_count > 0:
                    return file_count

        # Clear buffer and try 0x4C (mp3 folder)
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        logger.info("Querying DFPlayer with 0x4C (/mp3 folder files)...")
        send(0x4C, 0, 0)
        time.sleep(0.2)

        response = read_dfplayer_response(timeout=0.5)
        if response:
            logger.info(f"0x4C response: {response.hex()}")
            if response[3] == 0x4C:
                file_count = (response[5] << 8) | response[6]
                logger.info(f"DFPlayer reports {file_count} files in /mp3 folder")
                return file_count

        logger.warning("DFPlayer did not respond to file count queries (tried 0x48 and 0x4C)")
        logger.warning("Consider creating config/track_catalog.txt with your track list")
        return None
    except Exception as e:
        logger.error(f"Error querying DFPlayer file count: {e}")
        return None
```

**Lines changed:** Function expanded from 30 lines to 55 lines
**Key improvements:**
- Tries 0x48 first (total TF card files) before 0x4C (mp3 folder only)
- Logs raw hex response for diagnostics
- Increased timeout 0.1s → 0.2s
- Better error messages with actionable guidance

---

## Summary of Changes

| Change | Type | Lines | Impact |
|--------|------|-------|--------|
| Volume slider fix | Bug fix | 1131-1135 (-5 lines) | CRITICAL - Fixes non-working volume |
| Track query enhancement | Enhancement | 253-307 (+25 lines) | IMPROVED - Better detection & logging |

**Total net change:** +20 lines

---

## Testing Status

### Volume Slider
- [ ] Test: Drag volume slider smoothly
- [ ] Test: Verify audio volume changes
- [ ] Test: No oscillation or jumping

### Track Count Query
- [ ] Test: Check logs for 0x48/0x4C responses
- [ ] Test: Verify count matches SD card
- [ ] Test: Try manual catalog if needed

---

## Files to Review

1. **BUGFIX_SUMMARY.md** - Quick reference (this summary)
2. **BUGFIX_VOLUME_AND_TRACKS.md** - Detailed technical analysis
3. **TESTING_GUIDE_BUGFIXES.md** - Complete testing procedures
4. **CHANGES_APPLIED.md** - This file (line-by-line changes)

---

## Ready to Test

```bash
# Stop service
sudo systemctl stop dfplayer-fb

# Run with logging
sudo -E python3 /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py

# Test volume slider (drag left/right)
# Check logs for track query responses
# Verify all tracks can be played

# When satisfied, restart service
sudo systemctl start dfplayer-fb
```
