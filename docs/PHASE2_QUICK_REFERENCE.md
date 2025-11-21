# Phase 2 Quick Reference Card

## Issues to Fix

### 🔴 HIGH PRIORITY: Playback Reliability
**Problem:** Some tracks skip after 1 second, loop forever
**Files:** `src/dfplayer_fb_gui.py:429-434` (play_track_number)
**Fix:** Add response validation, error handling, rate limiting

### 🟡 MEDIUM PRIORITY: Auto-Advance
**Problem:** Songs don't auto-advance when finished
**Files:** `src/dfplayer_fb_gui.py:1057-1140` (main event loop)
**Fix:** Background serial reader thread + event processing

### 🟢 LOW PRIORITY: UI Text Overlap
**Problem:** Volume number and track info hidden behind track listing
**Files:** `src/dfplayer_fb_gui.py:649-756` (draw_ui)
**Fix:** Adjust Z-order rendering or reposition text

---

## Implementation Checklist

### Phase 2A: Playback Reliability (1-2 hours)
- [ ] Add `response = read_dfplayer_response()` to play_track_number()
- [ ] Check response for errors (0x40), log error codes
- [ ] Add `reset_dfplayer()` function with 0x0C command
- [ ] Add `last_play_cmd` timestamp and MIN_PLAY_INTERVAL check
- [ ] Test all 14 tracks, document success/fail patterns

### Phase 2B: Auto-Advance (1-2 hours)
- [ ] Create `dfplayer_listener_thread()` background thread
- [ ] Add global `dfplayer_events` queue
- [ ] Check for 0x3D (track finished) responses
- [ ] Process events in main loop
- [ ] Call `advance_track(1)` on track_finished event
- [ ] Test continuous playback through playlist

### Phase 2C: UI Polish (30 minutes)
- [ ] Move volume text to Y=240 (above slider) or X=230 (right of slider)
- [ ] Reorder draw_ui() to draw track info AFTER track listing
- [ ] Add Z-order comments to draw_ui() function
- [ ] Visual test on hardware

---

## Code Snippets

### Response Validation
```python
def play_track_number(track_no):
    send(0x03, track_no >> 8, track_no & 0xFF)
    time.sleep(0.2)
    response = read_dfplayer_response(timeout=0.3)
    if response and response[3] == 0x40:
        logger.error(f"DFPlayer error: {response[6]:02x}")
        return False
    return True
```

### Auto-Advance Thread
```python
def dfplayer_listener_thread():
    while True:
        if ser and ser.in_waiting >= 10:
            response = read_dfplayer_response(timeout=0.1)
            if response and response[3] == 0x3D:  # Track finished
                dfplayer_events.put({"event": "track_finished"})
        time.sleep(0.05)
```

### Main Loop Event Processing
```python
while True:
    # Process DFPlayer events
    while not dfplayer_events.empty():
        event = dfplayer_events.get_nowait()
        if event["event"] == "track_finished":
            advance_track(1)
            play_track_number(get_selected_track()["number"])

    # ... touch event processing ...
```

---

## Testing Commands

```bash
# Pull Phase 2 code when ready
cd /home/pi/pi-tft-dfplayer
git pull origin refactor/phase1-code-quality
sudo systemctl restart dfplayer-fb

# Monitor playback logs
sudo journalctl -u dfplayer-fb -f | grep -E "(Track|error|ACK|0x40)"

# Check serial communication
sudo journalctl -u dfplayer-fb -f | grep -E "(0x3D|finished|advancing)"

# Test auto-advance
# Play track 1, wait for finish, confirm track 2 starts

# Test rapid clicking
# Rapidly click play button, confirm only one command sent
```

---

## Expected Log Output

### Successful Playback
```
INFO: Track 5 started successfully
INFO: Track finished, auto-advancing...
INFO: Track 6 started successfully
```

### Failed Playback (with error codes)
```
ERROR: DFPlayer error playing track 3: code 02
WARNING: Resetting DFPlayer module...
INFO: Track 4 started successfully
```

### Rate Limiting
```
DEBUG: Play command for track 7
DEBUG: Ignoring rapid play command
DEBUG: Ignoring rapid play command
```

---

## DFPlayer Error Codes

| Code | Description |
|------|-------------|
| 0x01 | Module busy |
| 0x02 | Module sleeping |
| 0x03 | Serial receive error |
| 0x04 | Checksum error |
| 0x05 | Specified track out of range |
| 0x06 | Specified track not found |
| 0x07 | Insert error |
| 0x08 | SD card reading failed |

---

## File Locations

**Main Application:** `src/dfplayer_fb_gui.py` (1140 lines)
- Line 224-251: `read_dfplayer_response()` ✅ Already implemented
- Line 253-307: `query_dfplayer_file_count()` ✅ Already implemented
- Line 429-434: `play_track_number()` ← MODIFY in Phase 2A
- Line 649-756: `draw_ui()` ← MODIFY in Phase 2C
- Line 1057-1140: Main event loop ← MODIFY in Phase 2B

**New Functions to Add:**
- `reset_dfplayer()` (Phase 2A)
- `dfplayer_listener_thread()` (Phase 2B)

---

## Success Criteria

### Phase 2A Complete When:
✅ All 14 tracks play reliably (95%+ success rate)
✅ Error codes logged when failures occur
✅ Rapid clicking doesn't cause issues
✅ DFPlayer resets automatically on errors

### Phase 2B Complete When:
✅ Track 1 auto-advances to Track 2 on finish
✅ Entire playlist plays through without user input
✅ No track skipping between songs

### Phase 2C Complete When:
✅ Volume number visible (not hidden)
✅ Track info visible (not hidden)
✅ All UI text readable at a glance

---

## Git Workflow

```bash
# Continue on same branch
git checkout refactor/phase1-code-quality

# After each phase:
git add .
git commit -m "feat: Phase 2A - Playback reliability improvements"
git push origin refactor/phase1-code-quality

# Final merge after Phase 2 complete
git checkout main
git merge refactor/phase1-code-quality
git push origin main
```

---

## Total Estimated Time

- Phase 2A: 1-2 hours development + 30 min testing = **~2 hours**
- Phase 2B: 1-2 hours development + 30 min testing = **~2 hours**
- Phase 2C: 30 min development + 10 min testing = **~40 min**

**Total: ~5 hours** for complete Phase 2 implementation and testing
