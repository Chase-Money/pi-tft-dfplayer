# Architecture and Design

This document consolidates all architectural design, implementation planning, and system design documentation for the pi-tft-dfplayer project.

## System Architecture Overview

### Current Architecture (v2 Framework)
- **Entry Point**: `src/main.py` (uses app.Application + Config + TouchController + ScreenManagerV2)
- **Hardware Boundaries**: Framebuffer, touch, DFPlayer in `src/hardware/` and `src/backends/`, UI in `src/ui/`
- **Unified Framework**: ScreenManagerV2 + FramebufferRendererV2 + AppState/Config v2

### Component Architecture

```
┌───────────────────────────────────────────────────┐
│         USER INTERFACE LAYER (5 Screens)          │
├───────────────────────────────────────────────────┤
│         Screen Manager (State Machine)            │
└───────────────────┬───────────────────────────────┘
                    │
┌───────────────────┴───────────────────────────────┐
│         PRESENTATION LAYER                        │
│  - Event Bus (Pub/Sub Pattern)                     │
│  - Widget Library                                 │
│  - Gesture Recognition                            │
└───────────────────┬───────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        │                       │
┌───────▼────────┐    ┌────────▼─────────┐
│   DFPlayer     │    │    Spotify       │
│   Backend      │    │    Backend       │
│   (UART)       │    │    (librespot)   │
└───────┬────────┘    └────────┬─────────┘
        │                       │
        │              ┌────────▼─────────┐
        │              │   PulseAudio     │
        │              │   Audio Router   │
        │              └────────┬─────────┘
        │                       │
        │         ┌─────────────┴──────────┐
        │         │                         │
┌───────▼─────┐  ┌▼────────┐    ┌─────────▼──┐
│  Wired      │  │Bluetooth│    │   ALSA     │
│  Speaker    │  │ A2DP    │    │   Output   │
└─────────────┘  └─────────┘    └────────────┘
```

## DFPlayer Mini Integration

### Critical Understanding
The DFPlayer Mini is a **STANDALONE Module** that:
- Reads MP3/WAV files from its own SD card
- Decodes and plays audio independently
- Has its own microcontroller
- Communicates via UART serial protocol

**What the Pi CANNOT do:**
- ❌ Read files from DFPlayer's SD card
- ❌ See file names on DFPlayer's SD card
- ❌ Access DFPlayer's filesystem
- ❌ Know what files exist without querying

### Current Implementation Limitations
1. **One-Way Communication**: Pi sends commands but never reads responses
2. **No Status Feedback**: Cannot detect playback state or errors
3. **Limited Error Handling**: No validation of command success

## Implementation Roadmap

### Phase 1: Core Refactoring (Current)
**Goals:**
- Modularize codebase (core/, hardware/, backends/, ui/)
- Extract hardware abstractions
- Implement event bus pattern
- Create abstract backend interface
- Achieve 80% test coverage

**Entry Criteria:** ✅ All met
- Critical bugs fixed
- Tests in place
- Architecture documented

### Phase 2: UI Framework
- Build ScreenManager
- Create widget library
- Implement gesture recognition
- Deliver 3-screen navigation

### Phase 3: Bluetooth Audio
- Bluetooth pairing workflow
- Audio routing with PulseAudio
- Settings screen
- Device persistence

### Phase 4: Spotify Integration
- Install librespot
- MPRIS D-Bus control
- Spotify UI screen
- Authentication flow

### Phase 5: Integration & Polish
- Backend switching
- Performance optimization
- Artwork caching
- Production deployment

## Technology Stack

### Core (Existing)
- Python 3.9+, PIL, pyserial, evdev
- Direct framebuffer rendering (RGB565)
- UART communication with DFPlayer Mini

### New Additions
- **Spotify:** librespot + dbus-python + PyGObject
- **Bluetooth:** BlueZ + PulseAudio + pybluez
- **Testing:** pytest + pytest-mock + coverage
- **UI Framework:** Custom ScreenManager + Event Bus

## UI Screen Design

### 5-Screen Architecture

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

## Risk Assessment

### High Priority Risks
1. **Memory constraints** on Pi Zero 2 W (512MB RAM)
   - Mitigation: Profile early, limit caches, optimize PIL usage

2. **Bluetooth audio latency** (200-300ms)
   - Mitigation: Document limitation, use aptX if available

3. **Spotify authentication complexity**
   - Mitigation: Multiple auth strategies planned

### Medium Priority Risks
1. **Hardware reliability** (UART, touch, display)
   - Mitigation: Robust error handling, graceful degradation

2. **Performance bottlenecks** (UI rendering, event processing)
   - Mitigation: Profile early, optimize critical paths

## Success Metrics

| Metric | Target | Current Status |
|--------|--------|----------------|
| Code Quality | 85/100 | ✅ PASS (85/100) |
| Test Coverage | 80% | 🔄 IN PROGRESS (~60%) |
| Documentation | 100% | ✅ PASS |
| Resource Cleanup | 100% | ✅ PASS |
| Error Handling | 90% | ⚠️ GOOD (85%) |

## Future Development Roadmap

For planning of major new features and significant improvements, refer to reliability_spotify.md for:
- UI rendering performance improvements
- Hardware communication robustness
- Spotify integration strategies
- Step-by-step implementation guides

## Refactoring Plan (Current)

### Immediate Priorities
1. **Consolidate Versioned Files:** Remove legacy files, rename adopted _v2/_v3 files to canonical names
2. **Refactor DFPlayer Backend:** Eliminate duplication, implement interface, add event polling
3. **Consolidate Font Loading:** Handle exclusively in renderer, plumb through services

### Long-term Goals
- Migrate monolith logic into screens/components
- Wire touch/events/backends properly
- Delete superseded files, update docs

---

*This document consolidates information from: IMPLEMENTATION_ROADMAP.md, DFPLAYER_ARCHITECTURE.md, PHASE_2_IMPLEMENTATION_SUMMARY.md, PHASE2_UI_PLAN_v2.md, reliability_spotify.md, and related design documents.*</content>
<parameter name="filePath">docs/ARCHITECTURE_AND_DESIGN.md
