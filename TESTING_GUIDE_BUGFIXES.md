# Testing Guide for Bug Fixes

## Changes Made

### Fix 1: Volume Slider (Lines 1131-1135)
**Problem:** Duplicate volume calculation causing oscillation
**Solution:** Removed redundant code, now only calls `update_volume_from_x(px)`

### Fix 2: Track Count Query (Lines 253-307)
**Problem:** Query returns 3 tracks when 5+ exist
**Solution:** Enhanced query with dual-method approach (0x48 and 0x4C) and detailed logging

---

## Testing Procedure

### Pre-Test Checklist
1. Ensure DFPlayer SD card is properly inserted
2. Verify system service is stopped:
   ```bash
   sudo systemctl stop dfplayer-fb
   ```
3. Check serial port permissions:
   ```bash
   ls -l /dev/serial0
   groups $USER  # Should include 'dialout' group
   ```

### Test 1: Volume Slider Fix (CRITICAL)

**Expected Behavior:**
- Volume slider should respond smoothly to touch and drag
- Audio volume should change audibly
- No oscillation or jumping between values
- Volume display number should update correctly

**Test Steps:**
```bash
# Run with full logging
sudo -E python3 /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py
```

1. Touch the volume bar (yellow bar, Y=260)
2. Drag left and right slowly
3. Verify:
   - Slider fills/empties smoothly
   - Number updates correctly (00-30)
   - Audio volume changes (if playing)
   - No jumping or oscillation

**Success Criteria:**
- Smooth visual feedback
- Audible volume change
- Consistent behavior across multiple drags

**If Test Fails:**
- Check logs for vol_set() calls
- Verify VOLBAR_RECT = (20, 260, 200, 24)
- Check if update_volume_from_x() is being called

---

### Test 2: Track Count Query Enhancement

**Expected Behavior:**
- Logs should show both 0x48 and 0x4C query attempts
- File count should match actual SD card contents
- If both queries fail, fallback catalog should be used

**Test Steps:**
```bash
# Run with logging to see query details
sudo -E python3 /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py 2>&1 | grep -A5 "Querying DFPlayer"
```

**What to Look For in Logs:**
```
INFO - Querying DFPlayer with 0x48 (total TF card files)...
INFO - 0x48 response: 7eff064800000005xxef
INFO - DFPlayer reports 5 total files on TF card
```

Or if 0x48 fails:
```
INFO - Querying DFPlayer with 0x48 (total TF card files)...
INFO - Querying DFPlayer with 0x4C (/mp3 folder files)...
INFO - 0x4C response: 7eff064c00000003xxef
INFO - DFPlayer reports 3 files in /mp3 folder
```

**Verify SD Card Contents:**
```bash
# If SD card is mounted at /media/pi/SDCARD
ls -la /media/pi/SDCARD/mp3/
# Or wherever your DFPlayer SD card is mounted
```

Count actual files and compare with logged count.

**Success Criteria:**
- Query response logged (0x48 or 0x4C)
- File count matches reality OR
- Clear warning about fallback catalog

---

### Test 3: Track Playback Verification

**Purpose:** Verify tracks 4 and 5 can still be played even if query shows different count

**Test Steps:**
1. Start application
2. Note how many tracks appear in track list panel
3. Try playing each track in sequence
4. If tracks 4-5 don't appear in list but exist on SD card:
   - Check if manual catalog file helps

**Create Manual Catalog (if needed):**
```bash
# Create catalog file
cat > /Users/chase/pi-tft-dfplayer/config/track_catalog.txt << 'EOF'
1|Track 0001
4|Track 0004
5|Track 0005
EOF

# Restart application
sudo -E python3 /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py
```

**Success Criteria:**
- All actual tracks can be played
- Track list matches actual SD card contents
- Manual catalog works as override if needed

---

## Diagnostic Commands

### Check DFPlayer SD Card Contents
```bash
# Find SD card mount point
lsblk
df -h | grep media

# List mp3 folder contents
ls -lh /media/pi/SDCARD/mp3/  # Adjust path as needed

# Count files
ls /media/pi/SDCARD/mp3/*.mp3 | wc -l
```

### Check Serial Communication
```bash
# Monitor serial data (stop application first)
sudo cat /dev/serial0 | xxd

# Check UART configuration
sudo raspi-config nonint get_serial_hw
sudo raspi-config nonint get_serial_cons
```

### View Full Application Logs
```bash
# Run and save full log
sudo -E python3 /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py 2>&1 | tee test.log

# Filter for relevant sections
grep "volume\|Volume" test.log
grep "DFPlayer\|track" test.log
```

---

## Expected Log Output (Success)

### Volume Slider Working:
```
INFO - Touch device initialized: ADS7846 Touchscreen
INFO - Serial port initialized successfully
INFO - Loaded 5 tracks from catalog file: config/track_catalog.txt
# When dragging volume:
# (No repeated vol_set calls, smooth updates)
```

### Track Query Working (0x48 Success):
```
INFO - No track catalog file found, querying DFPlayer...
INFO - Querying DFPlayer with 0x48 (total TF card files)...
INFO - 0x48 response: 7eff064800000005fe00ef
INFO - DFPlayer reports 5 total files on TF card
INFO - Auto-generating catalog for 5 tracks from DFPlayer
INFO - Loaded 5 tracks from catalog
```

### Track Query Working (0x4C Fallback):
```
INFO - No track catalog file found, querying DFPlayer...
INFO - Querying DFPlayer with 0x48 (total TF card files)...
INFO - Querying DFPlayer with 0x4C (/mp3 folder files)...
INFO - 0x4C response: 7eff064c00000003fe00ef
INFO - DFPlayer reports 3 files in /mp3 folder
INFO - Auto-generating catalog for 3 tracks from DFPlayer
```

---

## Troubleshooting

### Volume Still Not Working
1. Verify the fix was applied:
   ```bash
   grep -A5 "if drag_vol:" /Users/chase/pi-tft-dfplayer/src/dfplayer_fb_gui.py | tail -6
   ```
   Should show only 5 lines (not 10)

2. Check touch calibration:
   ```bash
   cat ~/.dfplayer_touch.json
   ```

3. Test with fresh calibration (tap CAL button on screen)

### Track Count Still Wrong
1. **Check actual SD card files:**
   - Are they in /mp3/ folder?
   - Sequential numbering (0001, 0002, 0003...)?
   - Or gaps (0001, 0004, 0005)?

2. **If gaps exist:** This is normal! DFPlayer counts files (3) not highest number (5)
   - Solution: Create manual catalog file

3. **If count is still wrong:**
   - Check logs for hex response
   - Response format: `7E FF 06 [CMD] 00 [HI] [LO] [CHK_HI] [CHK_LO] EF`
   - File count = (byte 5 << 8) | byte 6
   - Example: `7E FF 06 48 00 00 05 XX XX EF` = 5 files

### Serial Port Issues
```bash
# Check if serial port exists
ls -l /dev/serial0

# Check UART enabled
sudo raspi-config nonint get_serial_hw  # Should be 0 (enabled)

# Check console disabled
sudo raspi-config nonint get_serial_cons  # Should be 1 (disabled)

# Re-run system tweaks if needed
cd /Users/chase/pi-tft-dfplayer
./scripts/apply_system_tweaks.sh
sudo reboot
```

---

## Post-Test: Restore Service

After successful testing:
```bash
# Re-enable and start service
sudo systemctl enable dfplayer-fb
sudo systemctl start dfplayer-fb

# Check status
sudo systemctl status dfplayer-fb

# Monitor logs
sudo journalctl -u dfplayer-fb -f
```

---

## Summary Checklist

- [ ] Volume slider works smoothly
- [ ] Audio volume changes audibly
- [ ] Track query logs show hex response
- [ ] File count matches SD card OR manual catalog used
- [ ] All actual tracks can be played
- [ ] No crashes or errors in logs
- [ ] Service can be re-enabled successfully
