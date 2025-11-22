# Project Goals & Roadmap (Legacy)
Legacy goals. Use `docs/ai/PROJECT_GUIDE.md` for current objectives and `docs/ai/TASK_LOG.md` for tracking.
**Pi TFT DFPlayer - Touchscreen MP3 Player for Raspberry Pi**

**Last Updated:** 2025-11-12
**Current Branch:** refactor/phase1-code-quality
**Current Status:** Phase 1 Complete | Phase 2 Ready to Start

---

## 🎯 Vision

Transform the pi-tft-dfplayer from a functional DIY MP3 player into a production-quality, feature-rich music player with modern UX, robust playback, and extensibility for future enhancements (Spotify, Bluetooth).

---

## 📅 NEAR TERM GOALS (This Week/Sprint)

### Priority 1: Playback Reliability (HIGH PRIORITY - Immediate)
**Status:** Ready to implement
**Time Estimate:** 2-3 hours
**Branch:** Continue on `refactor/phase1-code-quality`

#### Objectives:
- **Fix intermittent playback failures** where tracks skip after 1 second
- **Implement DFPlayer response validation** to catch errors early
- **Add error recovery mechanisms** to handle DFPlayer error states
- **Prevent rapid-fire command issues** through rate limiting

#### Tasks:
1. ✅ Add response validation to `play_track_number()` function
   - Read and parse DFPlayer ACK/NACK responses
   - Check for error code 0x40 and log specific error codes
   - Return success/failure status

2. ✅ Implement `reset_dfplayer()` recovery function
   - Send reset command (0x0C)
   - Re-initialize volume and source selection
   - Call on startup and after consecutive failures

3. ✅ Add rate limiting for play commands
   - Track last play command timestamp
   - Enforce minimum 500ms interval between commands
   - Prevent user rapid-clicking issues

4. ✅ Hardware testing and logging
   - Test all 14 tracks on actual hardware
   - Document success/failure patterns
   - Identify problematic tracks/file issues

**Success Criteria:**
- 95%+ playback success rate across all tracks
- Clear error logging when failures occur
- No issues from rapid user interactions

**Files to Modify:**
- `src/dfplayer_fb_gui.py:429-434` (play_track_number)
- `src/dfplayer_fb_gui.py:1057-1140` (main event loop)

**Reference:** See `REMAINING_ISSUES.md` Section "Phase 2A"

---

### Priority 2: Auto-Advance Playback (MEDIUM PRIORITY - This Week)
**Status:** Ready to implement after Priority 1
**Time Estimate:** 2-3 hours

#### Objectives:
- **Enable continuous playlist playback** without manual intervention
- **Implement background serial monitoring** for DFPlayer events
- **Handle track-finished notifications** automatically
- **Smooth track transitions** from one song to the next

#### Tasks:
1. ✅ Create background serial reader thread
   - Monitor DFPlayer serial port for responses
   - Detect track-finished (0x3D) events
   - Queue events for main thread processing

2. ✅ Process DFPlayer events in main loop
   - Check event queue on each iteration
   - Handle "track_finished" event
   - Auto-advance to next track in catalog

3. ✅ Test continuous playback
   - Verify smooth transitions between tracks
   - Ensure no skipping or gaps
   - Test through entire 14-track playlist

**Success Criteria:**
- Playing track 1 automatically advances to track 2, then 3, etc.
- Entire playlist plays without user interaction
- No audio gaps or stuttering between tracks

**Files to Modify:**
- `src/dfplayer_fb_gui.py` (add new thread function)
- `src/dfplayer_fb_gui.py:1057-1140` (event processing in main loop)

**Reference:** See `REMAINING_ISSUES.md` Section "Phase 2B"

---

### Priority 3: UI Polish - Text Overlap Fixes (LOW PRIORITY - This Week)
**Status:** Ready to implement
**Time Estimate:** 30-40 minutes

#### Objectives:
- **Fix volume level visibility** (currently hidden behind track panel)
- **Fix track info visibility** (metadata obscured by panel overlap)
- **Improve Z-order rendering** for clearer visual hierarchy

#### Tasks:
1. ✅ Reposition volume text
   - Move above volume slider OR to the right of it
   - Ensure always visible

2. ✅ Reorder UI drawing operations
   - Draw track listing panel first
   - Draw track info/metadata on top
   - Document Z-order in code comments

3. ✅ Visual verification on hardware
   - Confirm all text is readable
   - Check no overlapping elements

**Success Criteria:**
- Volume number (0-30) is clearly visible
- Track info (title, artist) is readable
- All UI elements have proper visual hierarchy

**Files to Modify:**
- `src/dfplayer_fb_gui.py:649-756` (draw_ui function)

**Reference:** See `REMAINING_ISSUES.md` Section "Phase 2C"

---

### Priority 4: Code Quality Improvements (Ongoing)
**Status:** In progress
**Time Estimate:** Ongoing as part of other tasks

#### Objectives:
- Remove any remaining code bloat
- Improve code documentation
- Ensure consistent coding standards
- Optimize performance where possible

#### Tasks:
1. ✅ Review and remove unused imports
2. ✅ Add docstrings to all functions
3. ✅ Add type hints where missing
4. ✅ Remove commented-out code
5. ✅ Optimize repeated operations
6. ✅ Add inline comments for complex logic

**Success Criteria:**
- Clean, well-documented codebase
- No unused or dead code
- Consistent style throughout

---

## 📆 SHORT TERM GOALS (1-2 Months)

### Goal 1: Complete v2/v3 Module Consolidation
**Status:** Partially complete (v2/v3 variants exist)
**Time Estimate:** 1-2 weeks

#### Objectives:
- **Consolidate v2 and v3 modules** into canonical versions
- **Remove version suffixes** (_v2, _v3) from filenames
- **Update all imports** to use canonical module names
- **Ensure hardware profile selection works** seamlessly

#### Tasks:
1. ✅ Decide on canonical module structure
2. ✅ Merge improvements from v2/v3 into main modules
3. ✅ Archive obsolete versioned files
4. ✅ Update all import statements
5. ✅ Update systemd service files
6. ✅ Test both hardware profiles (touchscreen + ST7735 buttons)
7. ✅ Update documentation to reflect changes

**Success Criteria:**
- No more `_v2` or `_v3` suffixes in active code
- Both hardware profiles work correctly
- Clean module hierarchy
- Updated documentation

**Reference:** See `docs/DEV_CHECKPOINT_2025-11-12.md`

---

### Goal 2: Comprehensive Testing Suite
**Status:** Basic tests exist, needs expansion
**Time Estimate:** 1-2 weeks

#### Objectives:
- **Achieve 80%+ code coverage**
- **Add unit tests for all core modules**
- **Add integration tests for key workflows**
- **Set up CI/CD pipeline** for automated testing

#### Tasks:
1. ✅ Expand unit tests for:
   - `src/core/config.py`
   - `src/core/state.py`
   - `src/core/events.py`
   - `src/backends/dfplayer_backend.py`

2. ✅ Add integration tests for:
   - Full playback workflow
   - Touch calibration process
   - Volume control end-to-end
   - Track selection and playback

3. ✅ Set up GitHub Actions CI
   - Run tests on every commit
   - Generate coverage reports
   - Lint code with pylint/flake8

4. ✅ Add smoke test automation
   - Automated hardware smoke tests
   - Pre-deployment validation

**Success Criteria:**
- 80%+ code coverage
- All tests passing
- CI pipeline running automatically
- Clear test documentation

**Reference:** See `tests/README.md`, `TEST_PLAN.md`

---

### Goal 3: Enhanced UI/UX
**Status:** Planning phase
**Time Estimate:** 2-3 weeks

#### Objectives:
- **Implement modern color palette** with better contrast
- **Add icon-based controls** (play, stop, prev, next)
- **Create dedicated "Now Playing" area** with prominence
- **Add playback progress bar** (if DFPlayer supports position queries)
- **Implement basic gesture support** (long-press, swipe)

#### Tasks:
1. ✅ Visual refresh (Phase 1 from UI_IMPROVEMENT_PLAN.md)
   - Refined color palette
   - Better typography
   - Subtle visual feedback
   - Iconography for controls

2. ✅ Enhanced information display (Phase 2)
   - Dedicated "Now Playing" panel
   - Playback progress bar
   - Better metadata display

3. ✅ Gesture support
   - Long-press for fine volume control
   - Swipe for track navigation
   - Touch feedback animations

**Success Criteria:**
- Modern, visually appealing UI
- Improved information hierarchy
- Responsive touch interactions
- User testing positive feedback

**Reference:** See `UI_IMPROVEMENT_PLAN.md`

---

### Goal 4: Documentation & Developer Experience
**Status:** Good foundation, needs expansion
**Time Estimate:** Ongoing

#### Objectives:
- **Complete API documentation**
- **Create developer onboarding guide**
- **Add architecture diagrams**
- **Improve troubleshooting guides**

#### Tasks:
1. ✅ Complete API documentation for all modules
2. ✅ Create CONTRIBUTING.md guide
3. ✅ Add architecture diagrams to docs/
4. ✅ Expand troubleshooting guides
5. ✅ Create video tutorials for setup
6. ✅ Add inline code examples

**Success Criteria:**
- New developers can onboard easily
- All modules have clear API docs
- Troubleshooting guides cover common issues
- Active community contributions

---

## 🚀 LONG TERM GOALS (3-6 Months)

### Goal 1: Multi-Screen Navigation Framework
**Status:** Planned (IMPLEMENTATION_ROADMAP.md)
**Time Estimate:** 3-4 weeks

#### Objectives:
- **Implement ScreenManager** for view transitions
- **Create 5 distinct screens** (Home, Browser, Now Playing, Spotify, Settings)
- **Enable smooth screen transitions**
- **Implement navigation gestures** (swipe between screens)

#### Screens:
1. **Home Screen**: Choose between Spotify/MP3, access settings
2. **Track Browser**: Scrollable track/playlist list
3. **Now Playing**: Minimal interface with large artwork
4. **Spotify UI**: Playlist browser, search, queue (future)
5. **Settings**: Bluetooth pairing, calibration, system info

#### Tasks:
1. ✅ Design ScreenManager architecture
2. ✅ Create base View class
3. ✅ Implement each screen as separate View
4. ✅ Add screen transition animations
5. ✅ Implement navigation stack (back button support)
6. ✅ Test navigation flow

**Success Criteria:**
- Smooth transitions between all screens
- Intuitive navigation
- No performance degradation
- Clean separation of concerns

**Reference:** See `IMPLEMENTATION_ROADMAP.md` Phase 2

---

### Goal 2: Spotify Streaming Integration
**Status:** Planned
**Time Estimate:** 4-5 weeks
**Dependencies:** librespot, MPRIS D-Bus

#### Objectives:
- **Enable Spotify Premium streaming** over WiFi
- **Support Spotify Connect** (control from phone/desktop)
- **Browse playlists and search**
- **Display Spotify artwork and metadata**

#### Technical Approach:
- Use `librespot` as Spotify backend
- MPRIS D-Bus interface for control
- Dual-backend architecture (DFPlayer + Spotify)
- Backend switching from UI

#### Tasks:
1. ✅ Install and configure librespot
2. ✅ Implement Spotify backend abstraction
3. ✅ Create MPRIS D-Bus controller
4. ✅ Implement Spotify authentication flow
5. ✅ Add Spotify UI screen
6. ✅ Implement playlist browsing
7. ✅ Add search functionality
8. ✅ Test Spotify Connect mode

**Success Criteria:**
- Streaming works reliably over WiFi
- Spotify Connect functional
- Seamless backend switching
- Good user experience

**Risks:**
- Authentication complexity (may need phone/web flow)
- Network reliability requirements
- Spotify API rate limits

**Reference:** See `IMPLEMENTATION_ROADMAP.md` Phase 4

---

### Goal 3: Bluetooth Audio Output
**Status:** Planned
**Time Estimate:** 2-3 weeks
**Dependencies:** BlueZ, PulseAudio

#### Objectives:
- **Pair with Bluetooth speakers/headphones**
- **Seamless output switching** (wired ↔ Bluetooth)
- **Auto-reconnect** to last device on boot
- **Device management UI** (pair, unpair, forget)

#### Technical Approach:
- Use BlueZ for Bluetooth stack
- PulseAudio for audio routing
- Settings screen for device management
- Persistent device pairing info

#### Tasks:
1. ✅ Set up BlueZ and PulseAudio
2. ✅ Implement Bluetooth pairing workflow
3. ✅ Create audio output switcher
4. ✅ Add device management UI
5. ✅ Implement auto-reconnect logic
6. ✅ Test with multiple devices
7. ✅ Handle connection failures gracefully

**Success Criteria:**
- Can pair and connect to BT speakers
- Output switching works seamlessly
- Auto-reconnect reliable
- Good error handling

**Risks:**
- Bluetooth latency (200-300ms typical)
- Connection stability issues
- Multiple device management complexity

**Reference:** See `IMPLEMENTATION_ROADMAP.md` Phase 3

---

### Goal 4: Performance Optimization
**Status:** Future work
**Time Estimate:** 2-3 weeks

#### Objectives:
- **Optimize framebuffer rendering** for smoother UI
- **Reduce memory footprint** (Pi Zero 2 W has limited RAM)
- **Improve startup time**
- **Cache artwork efficiently**

#### Tasks:
1. ✅ Profile application performance
2. ✅ Optimize PIL drawing operations
3. ✅ Implement partial screen updates (dirty regions)
4. ✅ Add LRU cache for artwork
5. ✅ Reduce unnecessary redraws
6. ✅ Optimize serial communication timing
7. ✅ Lazy-load modules where possible

**Success Criteria:**
- Smooth 30+ FPS UI rendering
- Memory usage under 100MB
- Startup time under 3 seconds
- No frame drops during animations

---

### Goal 5: Advanced Features
**Status:** Future exploration
**Time Estimate:** Ongoing

#### Potential Features:
- **Playlist management**: Create, edit, save playlists
- **Queue management**: Reorder upcoming tracks
- **Equalizer**: Basic tone controls
- **Sleep timer**: Auto-shutdown after duration
- **Alarm/wake**: Play music at scheduled time
- **Visualizations**: Spectrum analyzer, waveforms
- **Multiple language support**
- **Themes/skins**: Customizable UI appearance

---

## 📊 Success Metrics

### Code Quality Metrics
| Metric | Current | Short-Term Target | Long-Term Target |
|--------|---------|-------------------|------------------|
| Test Coverage | ~60% | 80% | 90%+ |
| Code Quality Score | 85/100 | 90/100 | 95/100 |
| Import Consistency | 100% | 100% | 100% |
| Type Hint Coverage | 60% | 80% | 90% |
| Documentation | Good | Excellent | Complete |

### Feature Metrics
| Feature | Current Status | Near-Term | Short-Term | Long-Term |
|---------|---------------|-----------|------------|-----------|
| DFPlayer MP3 | ✅ Working | ✅ Reliable | ✅ Optimized | ✅ Perfect |
| Touch UI | ✅ Working | ✅ Polished | ✅ Multi-screen | ✅ Advanced |
| Volume Control | ✅ Fixed | ✅ Smooth | ✅ Enhanced | ✅ Perfect |
| Track Selection | ✅ Working | ✅ Reliable | ✅ Browser | ✅ Advanced |
| Auto-Advance | ❌ Missing | ✅ Working | ✅ Smooth | ✅ Perfect |
| Spotify | ❌ None | ❌ None | ❌ Planning | ✅ Working |
| Bluetooth | ❌ None | ❌ None | ❌ Planning | ✅ Working |

### User Experience Metrics
- **Playback Reliability**: Target 99%+ (Currently ~85%)
- **UI Responsiveness**: Target <100ms touch response (Currently good)
- **Battery Life**: N/A (wall-powered, but monitor power consumption)
- **Setup Time**: Target <15 minutes for new users

---

## 🎯 Immediate Action Items (Next Session)

1. **Implement Phase 2A: Playback Reliability**
   - Add response validation
   - Implement reset function
   - Add rate limiting
   - Test on hardware

2. **Implement Phase 2B: Auto-Advance**
   - Create background thread
   - Process events
   - Test continuous playback

3. **Implement Phase 2C: UI Polish**
   - Fix text overlap
   - Document Z-order
   - Visual verification

4. **Run Full Test Suite**
   - Verify no regressions
   - Update tests if needed
   - Document test results

---

## 📝 Notes & Considerations

### Hardware Limitations
- **RAM**: 512MB on Pi Zero 2 W (must keep memory usage low)
- **CPU**: Quad-core ARM Cortex-A53 @ 1GHz (adequate for current needs)
- **Storage**: SD card (affects artwork caching strategy)
- **Network**: WiFi only (no Ethernet on Zero 2 W)

### Technical Debt
- Legacy `dfplayer_fb_gui.py` monolith should eventually be fully modularized
- Touch calibration storage could use better format (JSON vs plain text)
- Hard-coded UI dimensions should become configurable
- Font paths hard-coded (should use resource path resolution)

### Future Hardware Support
- Larger displays (480x320 → 800x480)
- Capacitive touch (vs current resistive)
- Additional GPIO buttons
- External DAC for better audio quality
- Battery support (UPS HAT)

---

**Project Passphrase:** RAurelius2020<3

---

*This goals document is a living roadmap and will be updated as the project progresses.*
