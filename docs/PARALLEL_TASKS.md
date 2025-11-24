# Framework Migration - Parallel Development Tasks

**Created**: 2025-11-14
**Branch**: `feature/framework-migration`
**Goal**: Complete framework v2 migration and make ready for merge to main

## Work Streams Overview

Three parallel work streams have been identified to maximize development velocity:

- **Stream 1 (Claude/Primary)**: Critical bug fixes and core framework stability
- **Stream 2 (Developer A)**: UI/Calibration features and screens
- **Stream 3 (Developer B)**: Configuration system and testing infrastructure

---

## Stream 1: Critical Bug Fixes & Core Framework (PRIMARY)

**Assignee**: Claude (AI Assistant)
**Priority**: CRITICAL
**Estimated Time**: 2-3 hours
**Dependencies**: None - can start immediately

### Tasks

1. **Fix touch event payload structure** (CRITICAL - app crashes without this)
   - File: `src/main_tft_v2.py` lines 282-307
   - Issue: Events use `{"x": ..., "y": ...}` but widgets expect `{"pos": (x, y)}`
   - Fix: Standardize on `{"pos": (x, y)}` format throughout

2. **Add `shutdown()` method to DFPlayer backend**
   - File: `src/backends/dfplayer_v2.py` line 130
   - Issue: Widgets call `shutdown()` but backend only has `cleanup()`
   - Fix: Add alias method `shutdown = cleanup`

3. **Implement real track catalog loading**
   - File: `src/main_tft_v2.py` lines 160-169
   - Issue: Currently using mock/hardcoded track data
   - Fix: Load from text file (number|title format) or metadata JSON

4. **Add error handling for hardware initialization**
   - File: `src/main_tft_v2.py` method `initialize()`
   - Issue: Missing try/except for framebuffer/touch/serial failures
   - Fix: Graceful degradation and error reporting

5. **Fix resource cleanup in shutdown sequence**
   - File: `src/main_tft_v2.py` method `cleanup()`
   - Issue: Resources may not clean up in correct order
   - Fix: Ensure proper teardown sequence (stop threads → close hardware → cleanup UI)

6. **Add path validation for artwork loading**
   - File: `src/backends/dfplayer_v2.py` or artwork loading code
   - Issue: Potential path traversal vulnerability
   - Fix: Validate and sanitize artwork paths (use `os.path.abspath` + prefix check)

7. **Optimize widget rendering with dirty rect tracking**
   - Files: `src/ui/renderer_v2/widget.py`, `src/ui/renderer_v2/container.py`
   - Issue: Full screen redraws are inefficient
   - Fix: Track changed widgets, only redraw dirty regions

8. **Add integration tests**
   - File: `tests/integration/test_main_tft_v2.py` (new)
   - Tests: App initialization, touch event conversion, screen transitions
   - Goal: Ensure basic functionality works end-to-end

---

## Stream 2: UI Features & Calibration (DEVELOPER A)

**Assignee**: Developer A (Frontend/UI focus) — delivered: calibration screen, settings screen (orientation cycle + calibration entry), status overlays, smoother widgets (button flash, slider easing, drag scrolling). Pending: on-device calibration validation and error overlays across more screens.
**Priority**: HIGH
**Estimated Time**: 3-4 hours
**Dependencies**: Stream 1 task #1 (touch event structure) must be completed first

### Tasks

1. **Implement calibration screen UI** (BLOCKING MERGE)
   - File: `src/ui/screens_v2/calibration.py` (new file)
   - Requirements:
     - Display 4-point calibration targets (corners)
     - Collect raw touch coordinates at each target
     - Calculate transformation matrix (scale + offset for X/Y)
     - Save to `~/.touch_cal.txt` or config system
     - Visual feedback for each tap
   - Reference: Original implementation in `src/dfplayer_fb_gui.py` lines 529-604

2. **Add orientation configuration screen**
   - File: `src/ui/screens_v2/settings.py` (new or extend existing)
   - Requirements:
     - Cycle through 8 orientations (SWAP_XY × FLIP_X × FLIP_Y combinations)
     - Live preview of touch mapping
     - Save selected orientation to config
   - Reference: Original `dfplayer_fb_gui.py` lines 299-331

3. **Enhance main playback screen**
   - File: `src/ui/screens_v2/main_screen.py` (currently `now_playing.py`)
   - Improvements (partial):
     - Better visual feedback for button presses (press states) ✅ (button flash added)
     - Smooth volume slider transitions ✅ (slider easing added)
     - Track list scrolling with momentum/velocity 🚧 (list widget drag/scroll added; light inertia on drag end; could be tuned further)
     - Loading states for artwork ✅ (placeholder when absent)

4. **Add visual error feedback**
   - Status banner overlays added to Home/Track Browser/Now Playing; connects to app status messages. Broader coverage still recommended once backend raises richer errors.

### Testing Checklist for Developer A

- [ ] Calibration completes successfully on physical hardware (new flow: `Settings -> Calibrate`)
- [ ] All 8 orientations work correctly (cycle in Settings)
- [ ] Touch targets are appropriately sized (44px minimum for resistive touch)
- [ ] UI is readable at 480x320 on 3.5" screen
- [ ] Framebuffer rendering doesn't tear or flicker

---

## Stream 3: Configuration & Testing (DEVELOPER B)

**Assignee**: Developer B (Backend/Infrastructure focus)
**Priority**: HIGH
**Estimated Time**: 3-4 hours
**Dependencies**: None - can start immediately

### Tasks

1. **Implement configuration persistence system** (BLOCKING MERGE)
   - File: `src/core/config_v2.py` (DEPRECATED - now `src/core/config.py`)
   - Requirements:
     - Load/save configuration to `~/.dfplayer_config.json`
     - Settings to persist:
       - Touch calibration (scale_x, scale_y, offset_x, offset_y)
       - Touch orientation (swap_xy, flip_x, flip_y)
       - Volume level (last known state)
       - Last played track
       - UI theme/preferences
     - Thread-safe writes (use file locking or atomic writes)
     - Validation on load (handle corrupted config gracefully)
   - API Design:
     ```python
     # Note: config_v2 is now deprecated, use config instead
     from src.core.config import Config, get_config

     config = Config()
     config.load()

     # Get values with defaults
     volume = config.get("volume", default=15)

     # Set values
     config.set("volume", 20)
     config.set("touch_calibration", {...})

     # Persist to disk
     config.save()
     ```

2. **Add hardware abstraction tests**
   - File: `tests/unit/test_touch_controller.py` (new)
   - Mock evdev device, test coordinate transformation
   - Test calibration calculations
   - Test orientation transformations (all 8 modes)

3. **Add DFPlayer backend tests**
   - File: `tests/unit/test_dfplayer_backend.py` (new)
   - Mock serial port
   - Test command packet construction (checksum validation)
   - Test volume, track number boundary conditions
   - Test error handling for serial timeouts

4. **Create test fixtures and mock hardware**
   - File: `tests/fixtures/mock_hardware.py` (new)
   - Mock framebuffer device (in-memory RGB565 buffer)
   - Mock touch controller (programmable event sequence)
   - Mock DFPlayer serial (command log + responses)
   - Enables running test suite on desktop without Pi hardware

5. **Add CI/CD configuration**
   - File: `.github/workflows/test.yml` (if using GitHub)
   - Run unit tests on every push
   - Code coverage reporting
   - Linting (pylint, flake8, or ruff)

6. **Performance profiling**
   - File: `scripts/profile_rendering.py` (new)
   - Measure framebuffer push times
   - Measure widget render times
   - Identify bottlenecks (target: <16ms per frame for 60fps)

### Testing Checklist for Developer B

- [ ] Config survives corrupt file (creates new default)
- [ ] Config is thread-safe (no race conditions)
- [ ] All unit tests pass on desktop (without hardware)
- [ ] Code coverage > 80% on new framework code
- [ ] Performance profiling shows acceptable frame times

---

## Integration & Merge Checklist

Before merging `feature/framework-migration` → `main`, ensure:

- [ ] **All critical bugs fixed** (Stream 1 tasks 1-6)
- [ ] **Calibration UI implemented** (Stream 2 task 1)
- [ ] **Configuration system working** (Stream 3 task 1)
- [ ] **Real track loading works** (Stream 1 task 3)
- [ ] **Tests passing** (Stream 3 tasks 2-4)
- [ ] **Manual testing on hardware**:
  - [ ] App boots and shows UI
  - [ ] Touch calibration completes
  - [ ] Touch responds accurately across screen
  - [ ] DFPlayer commands control playback
  - [ ] Volume slider works
  - [ ] Track selection and playback work
  - [ ] App shuts down cleanly
- [ ] **No regressions** vs. original `dfplayer_fb_gui.py`
- [ ] **Documentation updated** (README, CLAUDE.md)

---

## Communication & Coordination

### Avoiding Merge Conflicts

- Stream 1 (Claude): Primarily modifying `main_tft_v2.py` and `dfplayer_v2.py`
- Stream 2 (Dev A): Creating new files in `src/ui/screens_v2/`
- Stream 3 (Dev B): Creating new files in `src/core/` and `tests/`

**Minimal overlap** - each stream works in different file areas.

### When Streams Complete

1. **Stream 1 completes first** → Push changes, unblocks Stream 2
2. **Stream 2 & 3 can merge in any order** → Both pull latest from Stream 1
3. **Final integration testing** → All developers test complete system

### Handoff Points

- Stream 1 → Stream 2: After touch event structure is fixed (task #1)
- Stream 3 → All: After config system is implemented (provides persistence API)

---

## Quick Start

### Developer A (UI Focus)
```bash
# Pull latest from branch
git checkout feature/framework-migration
git pull

# Wait for Stream 1 task #1 to complete (touch event structure fix)
# Check Slack/Discord for "touch events fixed" notification

# Create calibration screen
touch src/ui/screens_v2/calibration.py
# Reference: src/dfplayer_fb_gui.py lines 529-604

# Test on hardware
sudo -E python3 src/main_tft_v2.py
```

### Developer B (Config/Testing Focus)
```bash
# Pull latest from branch
git checkout feature/framework-migration
git pull

# Can start immediately - no dependencies

# Create config system (now consolidated in src/core/config.py)
# touch src/core/config_v2.py  # DEPRECATED

# Create test infrastructure
mkdir -p tests/unit tests/fixtures
touch tests/unit/test_touch_controller.py
touch tests/fixtures/mock_hardware.py

# Run tests
python3 -m pytest tests/
```

---

## Estimated Timeline

- **Hour 0-2**: Stream 1 (critical bugs) - BLOCKS Stream 2
- **Hour 2-5**: Stream 2 (UI/calibration) - parallel with Stream 1 tail + Stream 3
- **Hour 0-4**: Stream 3 (config/testing) - fully parallel with Stream 1
- **Hour 5-6**: Integration testing, bug fixes, polish
- **Hour 6**: Ready to merge to main

**Total wall-clock time**: ~6 hours (with 3 developers)
**Total development time**: ~10 hours (serial would take much longer)

---

## Questions or Issues?

- Stream 1 progress: Check git commits and todo list updates
- Coordination: Use project Slack/Discord channel
- Blockers: Tag team lead immediately
- Technical questions: Reference original `src/dfplayer_fb_gui.py` for implementation details
