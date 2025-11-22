# Bug Fixes for dfplayer_fb_gui.py (Legacy)
Legacy bugfix log. Record future fixes in `docs/ai/TASK_LOG.md` and align with `docs/ai/PROJECT_GUIDE.md`.

## Issue 1: Volume Slider Not Working (CRITICAL)

### Root Cause
Duplicate and conflicting volume calculation in the main event loop causing volume to oscillate.

**Location:** Lines 1131-1140 in `src/dfplayer_fb_gui.py`

### Problem Code
```python
if drag_vol:
    now = time.time()
    if now - last_drag > 0.02:
        update_volume_from_x(px)  # Line 1134 - Calls vol_set()
        vx, vy, vw, vh = VOLBAR_RECT
        clamped = max(vx, min(vx + vw, px))
        vol = int((clamped - vx) * 30 / vw)  # Line 1137 - WRONG calculation
        vol_set(vol)  # Line 1138 - Second vol_set() call
        draw_ui()
        last_drag = now
```

### Why It Breaks
1. `update_volume_from_x(px)` (line 1134) already:
   - Calculates volume with proper rounding: `int(round((clamped - x) * 30 / w))`
   - Calls `vol_set(vol)`
   - Calls `draw_ui()`

2. Lines 1136-1138 then:
   - Recalculate volume WITHOUT rounding: `int((clamped - vx) * 30 / vw)`
   - Call `vol_set(vol)` AGAIN with different value
   - This causes oscillation between two values

### Fix
Replace lines 1131-1140 with:

```python
if drag_vol:
    now = time.time()
    if now - last_drag > 0.02:
        update_volume_from_x(px)
        last_drag = now
```

Remove lines 1135-1139 (they duplicate what `update_volume_from_x()` already does).

---

## Issue 2: Track Count Query Returns 3 Instead of 5+

### Root Cause (Likely)
DFPlayer SD card may have:
- Only 3 actual files in `/mp3/` folder
- Tracks 4-5 exist elsewhere or with non-sequential numbering
- Example: `0001.mp3`, `0004.mp3`, `0005.mp3` = 3 files with gaps

### Why Tracks 4-5 Play Anyway
The play command `0x03` (line 503) sends absolute track number, which DFPlayer honors regardless of folder structure.

### Current Query Implementation
**Location:** Lines 253-282 in `src/dfplayer_fb_gui.py`

Uses command `0x4C` to query `/mp3` folder file count. This is correct per protocol.

### Diagnostic Steps

1. **Check actual SD card contents:**
   ```bash
   # On SD card, check what files exist
   ls -la /path/to/sdcard/mp3/
   ```

2. **Add logging to see raw response:**
   ```python
   response = read_dfplayer_response(timeout=0.5)
   if response:
       logger.info(f"Raw DFPlayer response: {response.hex()}")
       logger.info(f"Byte 3 (cmd): 0x{response[3]:02X}")
       logger.info(f"Bytes 5-6 (count): {(response[5] << 8) | response[6]}")
   ```

3. **Try alternative query command (0x48 for total TF card files):**

### Proposed Fix

Replace `query_dfplayer_file_count()` function (lines 253-282) with enhanced version:

```python
def query_dfplayer_file_count():
    """Query DFPlayer for number of files.

    Tries multiple query methods:
    1. Command 0x48 - Total files on TF card
    2. Command 0x4C - Files in /mp3 folder

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
        time.sleep(0.2)  # Increased from 0.1

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

        logger.warning("DFPlayer did not respond to file count queries")
        return None
    except Exception as e:
        logger.error(f"Error querying DFPlayer file count: {e}")
        return None
```

### Additional Investigation

If the fix above doesn't work, check:

1. **SD Card File Organization:**
   - Are files actually in `/mp3/` folder?
   - Are they named sequentially (0001.mp3, 0002.mp3...)?
   - Or do they have gaps (0001.mp3, 0004.mp3, 0005.mp3)?

2. **DFPlayer Behavior:**
   - Some DFPlayer clones count files differently
   - May need to query folder-by-folder if using folder mode
   - Command 0x4E (query files in folder 1-99) might be needed:
     ```python
     send(0x4E, 0, 1)  # Query folder 01
     ```

3. **Alternative: Manual Track Catalog**
   - Create `config/track_catalog.txt` with actual track numbers:
     ```
     1|Track One
     4|Track Four
     5|Track Five
     ```
   - This bypasses DFPlayer query entirely

---

## Summary

### Issue 1 (Volume) - CONFIRMED BUG
- **Severity:** Critical (broken functionality)
- **Cause:** Duplicate volume calculation code with incorrect math
- **Fix:** Remove lines 1135-1139, keep only `update_volume_from_x(px)` call
- **Confidence:** 100% - this is definitely the bug

### Issue 2 (Track Count) - LIKELY CAUSE IDENTIFIED
- **Severity:** High (UX issue, misleading track list)
- **Likely Cause:** SD card has 3 files, possibly non-sequential (1, 4, 5)
- **Fix Options:**
  1. Use command 0x48 instead of 0x4C for total file count
  2. Add detailed logging to diagnose actual response
  3. Use manual track catalog file
- **Confidence:** 80% - needs verification via logging

---

## Testing After Fix

### Volume Test
1. Touch and drag volume slider
2. Volume should change smoothly
3. Audio volume should audibly change
4. No oscillation or jumping values

### Track Count Test
1. Check logs for query response details
2. Verify actual SD card contents
3. Test if 0x48 returns different count than 0x4C
4. Confirm tracks 4-5 can still be played after fix
