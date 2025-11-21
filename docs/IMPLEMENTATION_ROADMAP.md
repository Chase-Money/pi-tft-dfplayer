# Implementation Roadmap
## Spotify Streaming + Bluetooth + Multi-Screen UI Expansion

**Project:** pi-tft-dfplayer Enhanced Edition
**Target Hardware:** Raspberry Pi Zero 2 W (512MB RAM, Quad-core ARM Cortex-A53 @ 1GHz)
**Timeline:** 8+ weeks
**Status:** Planning Phase

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Summary](#architecture-summary)
3. [Technology Stack](#technology-stack)
4. [Implementation Phases](#implementation-phases)
5. [Dependencies & Requirements](#dependencies--requirements)
6. [Risk Assessment](#risk-assessment)
7. [Success Metrics](#success-metrics)

---

## 🎯 Project Overview

### Current State (v0.2)
- ✅ Direct framebuffer rendering (RGB565)
- ✅ DFPlayer Mini MP3 playback via UART
- ✅ Touch input with calibration
- ✅ Single-screen UI with volume control
- ✅ Track metadata & album artwork support

### Target State (v1.0)
- ✅ **Spotify streaming** via WiFi (librespot)
- ✅ **Bluetooth audio** output (speakers & headphones)
- ✅ **5-screen UI** with intuitive navigation
- ✅ **Dual-source playback** (MP3 + Spotify)
- ✅ **Enhanced UX** with gestures and animations
- ✅ **Production-ready** code quality

### New Features

#### 1. Spotify Integration
- Stream music over WiFi using Spotify Premium account
- Spotify Connect support (control from phone/desktop)
- Browse playlists, search, and queue management
- Display album artwork and metadata

#### 2. Bluetooth Audio Output
- Pair with Bluetooth speakers and headphones
- Seamless switching between wired and Bluetooth
- Device management (pair, unpair, reconnect)
- Automatic reconnection to last device

#### 3. Multi-Screen UI (5 Screens)

**Home Screen:**
- Choose between Spotify or MP3 playback
- Large, touch-friendly buttons
- Settings access

**Track Browser:**
- Scrollable list of available tracks
- Works for both Spotify playlists and MP3 files
- Track selection with preview info

**Now Playing:**
- Minimal interface with large album art
- Essential controls: Play/Pause, Previous, Next
- Track progress indicator
- Return to browser

**Spotify UI:**
- Playlist browser
- Search functionality
- Queue management
- Spotify-specific features

**Settings:**
- Bluetooth device pairing
- Audio output selection
- Display calibration
- Volume presets
- System information

---

## 🏗️ Architecture Summary

### Component Diagram

```
┌─────────────────────────────────────────────────────┐
│           USER INTERFACE LAYER (5 Screens)          │
├─────────────────────────────────────────────────────┤
│         Screen Manager (State Machine)              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────┐
│          PRESENTATION LAYER                         │
│  • Framebuffer Renderer (PIL → RGB565)              │
│  • Touch Input Manager (evdev + gestures)           │
│  • Widget System (buttons, lists, sliders)          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────┐
│          BUSINESS LOGIC LAYER                       │
│  • Playback Controller (abstract interface)         │
│  • Audio Router (wired ↔ Bluetooth)                │
│  • Configuration Manager (JSON persistence)         │
│  • Event Bus (pub/sub pattern)                      │
└───────┬─────────────────────┬───────────────────────┘
        │                     │
┌───────▼─────────┐   ┌───────▼─────────┐
│  DFPlayer       │   │   Spotify       │
│  Backend        │   │   Backend       │
│  (UART)         │   │   (MPRIS)       │
└─────────────────┘   └─────────────────┘
        │                     │
┌───────┴─────────────────────┴───────────────────────┐
│          HARDWARE LAYER                             │
│  • DFPlayer (UART) • ALSA • BlueZ • WiFi            │
└─────────────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Abstract Backend Interface** - Unified API for DFPlayer and Spotify
2. **Event Bus** - Decoupled communication between components
3. **State Machine** - Screen navigation with history
4. **Strategy Pattern** - Pluggable audio routing
5. **Singleton Config** - Centralized configuration management

---

## 🛠️ Technology Stack

### Core Stack (Existing)
- **Python 3.9+** - Main application language
- **PIL (Pillow)** - Image rendering
- **pyserial** - DFPlayer UART communication
- **evdev** - Touch input processing

### New Dependencies

#### Spotify Integration
- **librespot** (v0.4.2) - Spotify playback daemon (Rust binary)
- **dbus-python** - D-Bus communication for MPRIS control
- **PyGObject** - GLib event loop integration

#### Bluetooth Audio
- **BlueZ** (5.55+) - Linux Bluetooth stack
- **PulseAudio** - Audio server and routing
- **pybluez** or **pydbus** - Python Bluetooth control

#### System Libraries
```bash
# Audio infrastructure
pulseaudio
pulseaudio-module-bluetooth
alsa-utils
libasound2-dev

# Bluetooth
bluez
bluez-tools
python3-bluez

# D-Bus
libdbus-1-dev
python3-dbus
python3-gi
```

### Audio Architecture

```
DFPlayer Mini ──────────▶ Hardware Speaker (SPK pins)
                         (Wired, direct connection)

Spotify (librespot) ──▶ ALSA ──▶ PulseAudio ──┬──▶ Bluetooth A2DP
                                                └──▶ ALSA (wired)
```

**Design Decision:** DFPlayer uses hardware speaker directly, Spotify uses software audio stack. Cannot play both simultaneously (acceptable limitation).

---

## 📅 Implementation Phases

### Phase 1: Core Refactoring (Week 1-2)
**Goal:** Prepare codebase for expansion without adding features

#### Tasks
- [ ] Fix all 6 critical bugs from code review
- [ ] Create modular directory structure (`core/`, `hardware/`, `backends/`, `ui/`)
- [ ] Extract hardware abstractions:
  - [ ] `hardware/dfplayer.py` - DFPlayer interface
  - [ ] `hardware/touch.py` - Touch input
  - [ ] `hardware/framebuffer.py` - Display rendering
- [ ] Implement core modules:
  - [ ] `core/config.py` - JSON configuration
  - [ ] `core/state.py` - Application state
  - [ ] `core/events.py` - Event bus
- [ ] Create abstract backend interface (`backends/base.py`)
- [ ] Refactor existing code into `backends/dfplayer_backend.py`
- [ ] Migrate existing UI to `ui/screens/now_playing.py`
- [ ] Add resource cleanup (`atexit` handlers)
- [ ] Write migration script for old config files

#### Deliverables
- ✅ Refactored codebase with same functionality
- ✅ Zero regressions (all existing features work)
- ✅ Improved code quality (80/100 score)
- ✅ Comprehensive unit tests (50%+ coverage)

#### Testing
```bash
# Regression test suite
python3 -m pytest tests/test_dfplayer.py
python3 -m pytest tests/test_touch.py
python3 -m pytest tests/test_framebuffer.py

# Manual testing
sudo python3 src/main.py
# Verify: touch calibration, MP3 playback, volume control
```

---

### Phase 2: UI Framework (Week 3)
**Goal:** Build screen management and reusable widgets

#### Tasks
- [ ] Implement `ui/screen_manager.py`:
  - [ ] State machine for screen transitions
  - [ ] Navigation history stack
  - [ ] Screen lifecycle (on_enter, on_exit)
- [ ] Create `ui/widgets.py`:
  - [ ] Button widget (with touch detection)
  - [ ] List widget (scrollable, with scroll buttons)
  - [ ] Slider widget (for volume)
  - [ ] Image widget (for album art)
  - [ ] Text label widget
- [ ] Implement `ui/gestures.py`:
  - [ ] Tap detection
  - [ ] Drag detection
  - [ ] Swipe detection (optional)
  - [ ] Long-press detection (optional)
- [ ] Build new screens:
  - [ ] `ui/screens/home.py` - Home screen
  - [ ] `ui/screens/track_browser.py` - Track browser
  - [ ] Update `ui/screens/now_playing.py` - Enhanced now playing
- [ ] Connect screens with ScreenManager
- [ ] Add screen transition animations (fade/slide)

#### Deliverables
- ✅ Working 3-screen navigation (Home, Browser, Now Playing)
- ✅ Reusable widget library
- ✅ Gesture recognition system
- ✅ Smooth screen transitions

#### Testing
- Navigate between all screens
- Test touch responsiveness on each screen
- Verify back button functionality
- Test scroll gestures in track browser

---

### Phase 3: Bluetooth Audio (Week 4)
**Goal:** Add Bluetooth pairing and audio routing

#### Tasks
- [ ] Install and configure system dependencies:
  ```bash
  sudo apt-get install bluez bluez-tools pulseaudio pulseaudio-module-bluetooth
  ```
- [ ] Implement `hardware/bluetooth.py`:
  - [ ] Device discovery (scan for nearby devices)
  - [ ] Pairing workflow (PIN-less for most devices)
  - [ ] Connection management
  - [ ] Paired device persistence
  - [ ] Auto-reconnect on boot
- [ ] Implement `hardware/audio_router.py`:
  - [ ] Detect available audio sinks (PulseAudio)
  - [ ] Switch between wired and Bluetooth
  - [ ] Volume normalization across outputs
  - [ ] Audio sink monitoring
- [ ] Build `ui/screens/settings.py`:
  - [ ] Bluetooth device list (paired + available)
  - [ ] Pairing UI with progress indicator
  - [ ] Audio output selector (wired/Bluetooth)
  - [ ] Calibration shortcut
  - [ ] System info (IP, version, uptime)
- [ ] Add Bluetooth indicators to other screens
- [ ] Create `scripts/setup_bluetooth.sh` - Automated setup
- [ ] Configure PulseAudio auto-switching

#### Deliverables
- ✅ Working Bluetooth pairing workflow
- ✅ Seamless audio output switching
- ✅ Settings screen with device management
- ✅ Persistent paired devices

#### Testing
```bash
# Test Bluetooth pairing
1. Navigate to Settings → Bluetooth
2. Scan for devices
3. Pair with Bluetooth speaker
4. Play MP3 → verify audio on Bluetooth
5. Switch to wired → verify audio on wired speaker
6. Reboot → verify auto-reconnect

# Test edge cases
- Pair multiple devices
- Disconnect device while playing
- Out of range scenarios
```

---

### Phase 4: Spotify Integration (Week 5-6)
**Goal:** Add Spotify streaming capability

#### Tasks - Setup (Week 5)
- [ ] Install librespot:
  ```bash
  wget https://github.com/librespot-org/librespot/releases/download/v0.4.2/librespot-linux-armhf-static.tar.gz
  tar -xzf librespot-linux-armhf-static.tar.gz
  sudo mv librespot /usr/local/bin/
  ```
- [ ] Configure systemd service (`systemd/spotify-connect.service`)
- [ ] Implement `backends/spotify_backend.py`:
  - [ ] MPRIS D-Bus interface
  - [ ] Metadata retrieval (track, artist, album, artwork)
  - [ ] Playback control (play, pause, stop, next, prev)
  - [ ] Volume control via MPRIS
  - [ ] Playlist retrieval (via Spotify Web API)
- [ ] Add Spotify authentication flow
- [ ] Create `scripts/setup_spotify.sh` - Interactive setup wizard

#### Tasks - UI (Week 6)
- [ ] Build `ui/screens/spotify_ui.py`:
  - [ ] Playlist browser
  - [ ] Search interface (keyboard input)
  - [ ] Queue display
  - [ ] Now playing (Spotify-specific)
- [ ] Integrate Spotify backend with PlaybackController
- [ ] Update Home screen with Spotify option
- [ ] Update Track Browser for Spotify playlists
- [ ] Add Spotify status indicators

#### Deliverables
- ✅ Working Spotify playback
- ✅ Spotify Connect support (control from phone)
- ✅ Playlist browsing and search
- ✅ Metadata display with artwork
- ✅ Seamless backend switching

#### Testing
```bash
# Spotify Connect test
1. Start app → Select Spotify on Home screen
2. Open Spotify on phone
3. Look for "Pi TFT Player" in devices
4. Play track from phone
5. Verify: artwork and metadata appear on Pi screen
6. Control playback from Pi screen
7. Switch back to phone control

# Local Spotify control
1. Navigate to Spotify UI screen
2. Browse playlists
3. Search for artist/track
4. Play from Pi
5. Test next/previous
6. Test volume control

# Backend switching
1. Play Spotify track
2. Navigate to Home → Select MP3
3. Verify: Spotify stops, MP3 starts
4. Reverse test
```

---

### Phase 5: Integration & Polish (Week 7)
**Goal:** Integrate all features and optimize

#### Tasks
- [ ] Implement seamless backend switching:
  - [ ] Stop current backend before starting new one
  - [ ] Preserve volume across backends
  - [ ] Handle edge cases (network loss, device disconnect)
- [ ] Add Spotify artwork caching:
  - [ ] Download and cache album art locally
  - [ ] LRU cache with size limit
  - [ ] Placeholder for missing artwork
- [ ] Optimize UI rendering:
  - [ ] Dirty rectangle tracking
  - [ ] Rate limiting (30 FPS max)
  - [ ] Reuse PIL Image objects
  - [ ] Cache static UI elements
- [ ] Add comprehensive error handling:
  - [ ] Network timeouts
  - [ ] Bluetooth disconnections
  - [ ] Spotify auth failures
  - [ ] DFPlayer communication errors
- [ ] Implement logging system:
  - [ ] Replace all `print()` with `logger.*`
  - [ ] Log rotation
  - [ ] Debug mode toggle
- [ ] Create systemd services for all components:
  - [ ] Main app service
  - [ ] Spotify service
  - [ ] Watchdog service (monitor and restart)
- [ ] Write comprehensive documentation:
  - [ ] User manual
  - [ ] Developer guide
  - [ ] API documentation
  - [ ] Troubleshooting guide

#### Deliverables
- ✅ Production-ready system
- ✅ All features integrated and tested
- ✅ Optimized performance (<50% CPU, <400MB RAM)
- ✅ Complete documentation

#### Performance Testing
```bash
# System monitoring
top -p $(pgrep -f "python3 src/main.py")
# Target: <50% CPU during playback, <400MB RAM

# Memory leak test (24 hours)
sudo systemctl start dfplayer-fb
# Play music, navigate screens, switch backends
# Monitor: cat /proc/$(pgrep -f main.py)/status | grep VmRSS
# Should remain stable

# Stress test
# Switch backends 100 times
# Pair/unpair Bluetooth 20 times
# Navigate all screens 50 times
# Check for crashes, memory leaks
```

---

### Phase 6: Advanced Features (Week 8+)
**Goal:** Nice-to-have enhancements

#### Optional Features
- [ ] Playlist management (create, edit, delete)
- [ ] Favorites/liked songs (persistent storage)
- [ ] Queue management (reorder, remove)
- [ ] Sleep timer (auto-shutdown after X minutes)
- [ ] Gesture shortcuts:
  - [ ] Swipe left/right to skip tracks
  - [ ] Two-finger gesture for volume
  - [ ] Long-press for context menu
- [ ] Visualizations:
  - [ ] Spectrum analyzer
  - [ ] Waveform display
  - [ ] Album art animations
- [ ] Web interface:
  - [ ] Remote control via browser
  - [ ] Mobile app
  - [ ] API server (REST or WebSocket)
- [ ] Voice control (optional, resource-intensive)
- [ ] Last.fm scrobbling
- [ ] Podcast support

---

## 📦 Dependencies & Requirements

### Hardware Requirements
- Raspberry Pi Zero 2 W (512MB RAM minimum)
- 3.5" ILI9486 SPI TFT display with XPT2046 touch
- DFPlayer Mini module
- MicroSD card (16GB recommended, 8GB minimum)
- 5V 2.5A+ power supply
- Speaker (4-8Ω, 2-3W for DFPlayer)
- Bluetooth speaker/headphones (for Bluetooth feature)

### Software Requirements

#### System Packages
```bash
# Install script: scripts/install_all.sh

# Python & development
python3 (>= 3.9)
python3-pip
python3-dev

# Existing dependencies
python3-pil
python3-serial
python3-evdev

# Audio infrastructure
pulseaudio
pulseaudio-module-bluetooth
alsa-utils
libasound2-dev

# Bluetooth
bluez (>= 5.55)
bluez-tools
python3-bluez

# D-Bus
libdbus-1-dev
libdbus-glib-1-dev
python3-dbus
python3-gi

# Spotify (manual install)
librespot (v0.4.2+)
```

#### Python Packages
```python
# requirements.txt

# Existing
Pillow==10.1.0
pyserial==3.5
evdev==1.6.1

# New - Spotify
dbus-python==1.3.2
PyGObject==3.46.0

# New - Bluetooth
pybluez==0.23
pydbus==0.6.0

# New - Audio
pyalsaaudio==0.9.2  # Optional

# New - Utilities
requests==2.31.0     # Spotify Web API
cachetools==5.3.2    # Artwork caching
```

### Storage Requirements
```
Application code:        ~10 MB
Python dependencies:     ~50 MB
System libraries:        ~100 MB
Spotify cache:           ~100 MB (configurable)
Artwork cache:           ~20 MB
Music files (MP3):       Variable (user content)
Logs:                    ~10 MB
------------------------------------------
Total (excluding music): ~290 MB

Recommended: 16GB SD card (allows room for music and growth)
```

### Network Requirements
- WiFi 802.11 b/g/n (for Spotify streaming)
- Bluetooth 4.2 or higher (for audio output)
- Internet bandwidth: ~320 kbps (Spotify Premium quality)

---

## ⚠️ Risk Assessment

### High-Severity Risks

#### Risk 1: Memory Constraints
**Probability:** MEDIUM | **Impact:** HIGH

**Issue:** Pi Zero 2 W has only 512MB RAM. Multiple services (PulseAudio, librespot, Python) may exhaust memory.

**Memory Budget:**
```
System/kernel:     ~100 MB
PulseAudio:        ~30 MB
librespot:         ~50 MB
Python app:        ~80 MB
Artwork cache:     ~20 MB
Buffer:            ~100 MB
--------------------------
Total:             ~380 MB (acceptable)
```

**Mitigation:**
- Profile memory during development
- Limit artwork cache to 10 images
- Use lazy loading for track lists
- Configure 1GB swap file
- Consider PyPy for better memory efficiency
- Monitor with: `free -h` and adjust limits

#### Risk 2: Bluetooth Audio Latency
**Probability:** HIGH | **Impact:** MEDIUM

**Issue:** A2DP Bluetooth has 200-300ms latency, noticeable delay between UI and audio.

**Mitigation:**
- Document expected latency in user guide
- Use aptX codec if supported (lower latency)
- Offer wired audio as primary recommendation
- No UI animations tied to audio playback

#### Risk 3: Spotify Authentication Complexity
**Probability:** MEDIUM | **Impact:** HIGH

**Issue:** Spotify OAuth requires web callback, difficult on headless Pi.

**Mitigation:**
- **Strategy 1:** Use librespot's device authentication (simpler)
- **Strategy 2:** Pre-authenticate on desktop, copy credentials
- **Strategy 3:** Run temporary OAuth server during setup
- **Fallback:** Use raspotify with pre-configured credentials

### Medium-Severity Risks

#### Risk 4: UI Rendering Performance
**Probability:** LOW | **Impact:** MEDIUM

**Issue:** Redrawing 480x320 screen at 60 FPS may cause lag.

**Mitigation:**
- Implement dirty rectangle tracking
- Target 30 FPS (sufficient for UI)
- Cache static UI elements
- Use double buffering
- Profile with: `time python3 -m cProfile src/main.py`

#### Risk 5: librespot Stability
**Probability:** LOW | **Impact:** MEDIUM

**Issue:** librespot may crash, leaving UI unresponsive.

**Mitigation:**
- Run as separate process (not thread)
- Implement process monitoring
- Auto-restart with systemd
- Add manual restart in Settings
- Timeout D-Bus calls (5 seconds)

---

## 📊 Success Metrics

### Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Boot time | < 30s | Time to responsive UI |
| Touch latency | < 100ms | Touch → visual feedback |
| UI frame rate | ≥ 30 FPS | During animations |
| CPU (idle) | < 20% | `top` during playback |
| CPU (peak) | < 60% | Track change + UI redraw |
| Memory usage | < 400 MB | `free -h` |
| Spotify start | < 3s | Select track → audio |
| MP3 start | < 1s | Select track → audio |
| BT pairing | < 30s | Scan → connect |

### Functional Requirements Checklist

#### Core Features
- [ ] All 5 screens implemented and navigable
- [ ] MP3 playback maintained (existing feature)
- [ ] Spotify playback functional (new feature)
- [ ] Bluetooth pairing works (new feature)
- [ ] Audio output switching works (new feature)
- [ ] Touch calibration maintained (existing feature)
- [ ] Volume control works for both backends
- [ ] Album artwork displays correctly
- [ ] Configuration persists across reboots
- [ ] System recovers from crashes gracefully

#### Quality Targets
- [ ] Code test coverage > 70%
- [ ] Zero critical bugs at release
- [ ] Documentation 100% complete
- [ ] User acceptance score > 4/5
- [ ] System uptime > 99% (24-hour test)

### User Acceptance Criteria

- [ ] Can navigate all screens intuitively
- [ ] Touch targets are large enough (≥ 44x44 pixels)
- [ ] Text is readable at arm's length
- [ ] Album artwork loads quickly (<2s)
- [ ] Volume control is smooth and responsive
- [ ] Bluetooth pairing is straightforward
- [ ] Spotify authentication works on first try
- [ ] Settings are easy to find and change
- [ ] System provides clear error messages
- [ ] No UI freezes during normal operation

---

## 🚀 Getting Started

### For Developers

1. **Clone and setup:**
   ```bash
   git clone https://github.com/Chase-Money/pi-tft-dfplayer.git
   cd pi-tft-dfplayer
   git checkout feature/multi-screen-ui  # Create this branch
   ```

2. **Install dependencies:**
   ```bash
   ./scripts/install_all.sh
   ```

3. **Run code review fixes:**
   ```bash
   # See CODE_REVIEW_SUMMARY.md for priority order
   # Start with Phase 1 critical fixes
   ```

4. **Begin Phase 1 refactoring:**
   ```bash
   mkdir -p src/{core,hardware,backends,ui/screens,utils}
   # Follow modular structure from architecture document
   ```

### For Users

**Current stable version (v0.2):**
```bash
git clone https://github.com/Chase-Money/pi-tft-dfplayer.git
cd pi-tft-dfplayer
./scripts/install_prereqs.sh
./scripts/apply_system_tweaks.sh
sudo reboot
sudo systemctl enable --now dfplayer-fb
```

**Enhanced version (v1.0 - in development):**
- Check back in 8 weeks for beta release
- Watch GitHub releases for updates
- Star the repository to track progress

---

## 📝 Notes

### Design Decisions

1. **Monolithic Python app** (not microservices) for simplicity and lower resource usage
2. **Event bus pattern** for decoupled component communication
3. **Abstract backend interface** for easy addition of future music sources
4. **PulseAudio** for audio routing (industry standard, well-supported)
5. **librespot** over Spotipy (native playback, no separate player needed)
6. **JSON configuration** (no database) for simplicity and human-readability

### Known Limitations

1. Cannot play DFPlayer and Spotify simultaneously (hardware limitation)
2. Spotify requires Premium account (librespot requirement)
3. Bluetooth A2DP latency ~200-300ms (protocol limitation)
4. No touchscreen keyboard (use on-screen keyboard or phone for search)
5. Limited to 30 FPS for UI (SPI display bandwidth)

### Future Considerations

- Support for additional music sources (YouTube Music, Tidal, etc.)
- Multi-room audio synchronization
- Voice control integration
- Touchscreen keyboard implementation
- Album art visualizations/effects
- Party mode (vote on next track)
- Integration with home automation systems

---

## 📚 Additional Resources

- [Detailed Architecture Document](./ARCHITECTURE_DETAILED.md) - See agent output
- [Code Review Summary](./CODE_REVIEW_SUMMARY.md)
- [API Documentation](./docs/api.md) - To be created
- [User Guide](./docs/user_guide.md) - To be created
- [Contributing Guidelines](./CONTRIBUTING.md) - To be created

---

**Document Version:** 1.0
**Last Updated:** November 10, 2025
**Status:** Planning Phase Complete, Ready for Implementation
