# Phase 2 UI Plan (v2) (Legacy)
Legacy phase plan. Capture new plans in `docs/ai/PROJECT_GUIDE.md` and updates in `docs/ai/TASK_LOG.md`.

This document captures the concrete plan for Phase 2 (UI Framework) as outlined in IMPLEMENTATION_ROADMAP.md and adapts it to the current modular/v2 codebase.

## Goals
- Introduce a lightweight screen manager + widget layer that works with the refactored modules.
- Create placeholder Home / Track Browser / Now Playing screens that demonstrate navigation.
- Keep rendering logic modular (small screen classes, reusable widgets) and testable without hardware.
- Lay groundwork for future Spotify/Bluetooth screens without disturbing existing v1 UI.

## Deliverables (Phase 2 scope)
1. **Screen Manager** (`ScreenManagerV2`)
   - Stack-based navigation (push/pop/replace).
   - Lifecycle hooks (on_enter/on_exit).
   - Central event routing + render dispatch.
2. **Widget Library (v2)**
   - Basic button, list, slider widgets with drawing helpers.
   - Touch-friendly hit testing and callback wiring.
3. **Screens (v2)**
   - Home screen: choose source / go to browser.
   - Track browser: scrollable list placeholder.
   - Now playing: uses existing artwork/title/volume helpers for prototype.
4. **Tests & Docs**
   - Unit tests for ScreenManagerV2 (stack behavior, event routing).
   - Widget smoke tests (callbacks fire, selection update).
   - Update tests/README_v2.md after integration.

## Integration Strategy
- New code lives under `src/ui/framework_v2/` and `src/ui/screens_v2/` so it does not interfere with legacy UI.
- `src/main.py` will adopt the new manager once screens are ready; `src/main_v2.py` (1.44" variant) can reuse the widget helpers incrementally.
- Document the usage in README / future PRs. For now, the framework can be instantiated in small pilots or Dev harnesses.

## Progress & Next Tasks

- ✅ DFPlayer backend now emits playback events (track_finished/track_started/error) via `poll_event()`.
- ✅ `DFPlayerApp` drains those events in a worker thread so auto-advance works hands-off.
- ✅ ScreenManagerV2, widgets, and placeholder screens are in place and can be toggled via `DFPLAYER_UI_FRAMEWORK=1`.
- ✅ Track Browser screen now displays the real track list, syncs scroll offsets with application state, and plays tracks on tap via the ScreenManager.
- ✅ Now Playing screen hooks into the backend/state: play/pause button toggles playback, and the volume slider writes through to state + backend (tap to adjust for now).

Next up:
1. Move the blocking touch loop to the new framework/event loop so rendering and event processing share a unified pipeline.
2. Flesh out real widgets (button hitboxes, scroll area, title clipping) and hook them into playback controls.
3. Replace the placeholder Track Browser/Now Playing screens with versions backed by real state (selection, now playing, volume adjustments).
4. Add gesture support (swipe/drag) once the new loop is in place.

## Open Questions (Future Phases)
- Gesture recognition (Phase 2 optional, Phase 3 once Bluetooth arrives).
- Animations / dirty rect optimizations (Phase 5 per roadmap).
- Config-driven screen layout (beyond Phase 2 scope).
