# Kivy Migration (High-Level)

Goal: replace the current framebuffer-driven UI with a Kivy-based UI that preserves hardware backends (DFPlayer, touch, framebuffer) while gaining a richer widget system, animations, and theming.

## Guiding Principles
- Keep hardware/backends the same; swap only the UI/view layer.
- Maintain ScreenManager-style navigation and the existing state/config services.
- Ship incremental PRs with feature parity checkpoints; keep `main` stable.

## Prereqs & Environment
- System deps: SDL2 stack for Kivy (`libsdl2{,-image,-mixer,-ttf}`, `libgles2-mesa`, `libmtdev`, `python3-kivy`), verify Pi OS packages and GPU/GL support.
- Confirm Kivy runs headless or with DRM/GBM on fb1; fall back to X11 only if required.
- Decide packaging: vendor wheels vs apt install; document in `scripts/install_prereqs.sh`.

## Architecture Mapping
- App shell: Kivy `App` + `ScreenManager`; mirror current `ScreenManagerV2` routes (`home`, `now_playing`, `track_browser`, `settings`, `calibration`).
- State/config: reuse `src/core/state_v2.py` and `src/core/config.py` via thin adapters; no business logic in Kivy widgets.
- Backend services: inject DFPlayer backend and artwork/metadata loaders as singletons; avoid UI threads doing I/O.
- Rendering/theme: define a Kivy theme module that reads `themes/*.json` and maps to Kivy Colors/Fonts; reuse palette logic.
- Input/touch: bridge existing touch calibration/orientation thresholds into Kivy’s touch events; add tap debounce and hitbox logging hooks.

## Milestones / PRs
1) **Scaffold & Build Setup**: Ensure deps install on Pi; create minimal Kivy app with blank screens and service wiring; CI headless smoke test (xvfb).
2) **Navigation & State Wiring**: Implement ScreenManager with placeholders; wire state/config/backends; status banner/toast component.
3) **Now Playing & Transport**: Build playback controls, volume, track title/artwork; ensure DFPlayer events update UI.
4) **Browser & Settings**: Track list with scrolling; settings for theme, volume, touch calibration launcher.
5) **Calibration & Touch UX**: Port calibration flow with on-device validation; add tap/drag thresholds, optional debug overlay.
6) **Performance & Polish**: Profile fps and input latency; optimize layouts for 480x320; add theming samples (LCARS/retro); document migration/rollback.

## Testing & Ops
- Add headless Kivy smoke test (App loads, screen switch) gated behind env flag for CI.
- Keep unit tests for backends untouched; add adapter tests for Kivy service wiring.
- Hardware checklist: touch accuracy, back button, DFPlayer commands, fps/thermal check on Pi.

## Open Questions
- Which window provider on target Pi (sdl2 vs egl/gbm)? Need hardware trial.
- Do we keep framebuffer code for fallback mode alongside Kivy? (likely yes until Kivy stable).
- Asset pipeline for fonts/icons (ship bundled vs system fonts).
