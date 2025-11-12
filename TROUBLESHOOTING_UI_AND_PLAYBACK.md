# Troubleshooting Guide: UI & Playback Issues

## Fixed Issues ✓

### Volume Slider Spacing
**Status:** FIXED in commit `06c3cd5`

The volume slider now has proper spacing from the prev/next buttons:
- **Before:** Only 8px gap, volume text overlapped buttons
- **After:** 20px gap, clear separation, larger touch target (24px height)

**Pull this fix:**
```bash
cd /home/pi/pi-tft-dfplayer
git pull origin refactor/phase1-code-quality
sudo systemctl restart dfplayer-fb
```

---

## Outstanding Issues

### 1. Track Catalog (Infinite/Placeholder Tracks)

**Problem:** The track list shows generic "Track 001", "Track 002", etc. instead of reading actual tracks from the SD card.

**Root Cause:** No track catalog file found. The app is using fallback placeholder tracks (30 generic entries).

**Solution:** Create a track catalog file

#### Option A: Auto-generate from SD card
If your DFPlayer SD card has files named `0001.mp3`, `0002.mp3`, etc., create a catalog:

```bash
cd /home/pi/pi-tft-dfplayer
mkdir -p config

# Generate catalog from SD card file names
# (Replace /media/dfplayer with your SD card mount point)
ls /media/dfplayer/mp3/*.mp3 | sort | awk -F'/' '{
    filename = $NF
    gsub(/\.mp3$/, "", filename)
    num = int(filename)
    print num "|Track " num
}' > config/track_catalog.txt
```

#### Option B: Manual creation with proper names
Create `config/track_catalog.txt` with your actual track names:

```bash
nano /home/pi/pi-tft-dfplayer/config/track_catalog.txt
```

**Format:**
```
1|Song Title One
2|Another Great Song
3|Third Track Name
# Lines starting with # are comments
4|Fourth Song
```

Or space-separated (less preferred):
```
1 Song Title One
2 Another Great Song
3 Third Track Name
```

#### Track Catalog Search Locations
The app checks these paths in order:
1. Environment variable: `DFPLAYER_TRACK_CATALOG`
2. `<repo>/config/track_catalog.txt`
3. `/home/pi/dfplayer_tracks.txt`

**After creating the file:**
```bash
sudo systemctl restart dfplayer-fb
```

---

### 2. Intermittent Playback Failures

**Symptoms:** Some tracks play fine, others fail immediately. Pattern varies (e.g., 2 good, 3 bad, 1 good, etc.)

**Potential Causes:**

#### A. SD Card File Naming Issues ⚠️ MOST LIKELY
DFPlayer Mini requires **strict** file naming:
- Files MUST be in `/mp3/` folder on SD card root
- Files MUST be named exactly: `0001.mp3`, `0002.mp3`, ..., `0255.mp3`
- NO gaps in numbering
- NO other naming schemes

**Check your SD card structure:**
```bash
# Mount SD card and check
ls /media/dfplayer/mp3/

# Should see:
# 0001.mp3
# 0002.mp3
# 0003.mp3
# ...
```

**If files are named incorrectly:**
1. Backup your SD card
2. Reformat as FAT32
3. Create `/mp3/` folder
4. Rename files: `0001.mp3`, `0002.mp3`, etc.
5. Re-insert into DFPlayer

#### B. File Format Issues
**Supported formats:**
- MP3 (most reliable)
- WAV (32kHz, 16-bit recommended)

**Unsupported/Problematic:**
- Variable bitrate MP3 (some modules struggle)
- High bitrate MP3 (>320kbps)
- Non-standard sample rates

**Test with known-good files:**
```bash
# Create simple test tone MP3s to verify hardware
# Use a tool like ffmpeg:
ffmpeg -f lavfi -i "sine=frequency=440:duration=5" -ar 32000 -ab 128k /media/dfplayer/mp3/0001.mp3
```

#### C. SD Card Quality
- Use **Class 10** or better SD cards
- Avoid cheap/counterfeit cards
- Check for corruption: `fsck.vfat /dev/sdX1`

#### D. DFPlayer Module Issues
- Loose connections
- Power supply insufficient (needs stable 5V, 200-500mA)
- Module firmware issues (rare, but happens)

**Hardware diagnostics:**
```bash
# Check serial communication
sudo systemctl stop dfplayer-fb
sudo minicom -D /dev/serial0 -b 9600

# In the app logs:
sudo journalctl -u dfplayer-fb -f

# Look for:
# - "Failed to initialize DFPlayer"
# - "Serial timeout" errors
# - "DFPlayer not responding" warnings
```

#### E. Track Number vs File Mismatch
If your track catalog lists track 5, but there's no `0005.mp3` on the SD card, playback will fail silently.

**Ensure alignment:**
```bash
# Track catalog should match SD card files EXACTLY
diff <(cat config/track_catalog.txt | grep -v '^#' | awk -F'|' '{print $1}' | sort -n) \
     <(ls /media/dfplayer/mp3/*.mp3 | sed 's/.*\/\([0-9]*\)\.mp3/\1/' | sed 's/^0*//' | sort -n)
```

---

### 3. Text/UI Positioning (Minor)

**Issue:** Track listing or metadata text may appear slightly misaligned.

**Current Layout (480x320):**
- Left panel (buttons/volume): X=20-220
- Right artwork: X=260-460
- Right metadata: X=260-460, Y=230-302
- Track list panel: X=240-460, Y=50-250

**Potential conflicts:**
- Track panel (X=240) starts before artwork/metadata (X=260)
  - Intentional overlap for visual hierarchy
  - Track list should render *before* artwork so artwork sits on top

**If text is hidden:**
Check draw order in `draw_ui()` function (lines 649-756). Text drawn later appears on top.

---

## Testing Checklist

After applying fixes:

- [ ] Volume slider doesn't trigger prev/next buttons
- [ ] Volume slider is easy to grab and drag
- [ ] Track list shows correct names (not "Track 001")
- [ ] Track list matches SD card contents exactly
- [ ] All tracks listed in catalog play successfully
- [ ] Prev/Next navigation works through all tracks
- [ ] Playback doesn't fail randomly
- [ ] All UI text is readable and properly positioned

---

## Debug Commands

```bash
# Check track catalog loading
sudo systemctl stop dfplayer-fb
sudo python3 /home/pi/pi-tft-dfplayer/src/dfplayer_fb_gui.py 2>&1 | grep -i "track\|catalog"

# Monitor DFPlayer serial communication
sudo apt-get install minicom
sudo systemctl stop dfplayer-fb
sudo minicom -D /dev/serial0 -b 9600

# Check SD card filesystem
sudo fdisk -l  # Find SD card device
sudo fsck.vfat /dev/sdX1  # Check for errors

# Verify DFPlayer connection
ls -l /dev/serial0  # Should exist
sudo cat /dev/serial0  # Should not error

# Check framebuffer
ls -l /dev/fb1  # Should exist
cat /sys/class/graphics/fb1/virtual_size  # Should show 480,320
```

---

## Quick Fixes Summary

1. **Volume slider:** Pull latest code from `refactor/phase1-code-quality`
2. **Track catalog:** Create `config/track_catalog.txt` with actual track names
3. **Playback:** Verify SD card files are named `0001.mp3`, `0002.mp3`, etc. in `/mp3/` folder
4. **Quality:** Use Class 10 SD card, 128kbps MP3 files, stable power supply

---

## Need More Help?

1. Capture logs: `sudo journalctl -u dfplayer-fb -n 200 > ~/dfplayer-debug.log`
2. Share SD card structure: `find /media/dfplayer -type f > ~/sdcard-files.txt`
3. Share track catalog: `cat config/track_catalog.txt`
4. Note exact playback pattern: "Tracks 1-2 work, 3-5 fail, 6 works, etc."
