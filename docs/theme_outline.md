# Theme Integration Outline (LCARS + Retro)

Goal: wire the new theme engine and sample palettes into the framebuffer UI so users can choose `DFPLAYER_THEME=<name>` or config value to change the look without code edits.

## Prereqs
- Confirm `themes/` is deployed alongside the binary/service (`lcars_default.json`, `lcars_rpi.json`, `lcars_ha.json`).
- Fonts: ensure selected fonts exist or fall back gracefully (Antonio/Nunito/ShareTechMono). Provide a bundled fallback if missing.
- Env/config: `DFPLAYER_THEME` env var and `ui_theme` config key should be read before renderer init.

## Implementation Steps (hand-off to dev)
1) **Plumb Theme Loader**
   - File: `src/ui/theme.py` already loads JSON. At app startup, call `load_theme(env_or_config_value)` and keep a `theme` object in the UI state.
   - Source theme name from: env `DFPLAYER_THEME`, else config (`ui_theme`), else default.

2) **Replace Hardcoded Colors/Metrics**
   - Files: framebuffer renderer entrypoints (`src/dfplayer_fb_gui.py` or `src/ui/*` drawing modules).
   - Swap literals for palette values: bg/panel/text/text_dim/accents/status_good|warn|bad.
   - Use metrics: `radius_lg`, `radius_sm`, `stroke`, `padding`, `gap`, `touch_min`.
   - Use layout: `header_color`, `rail_color`, `button_primary/secondary`, `progress_height`, `volume_width`.

3) **Layout Helpers**
   - Add orientation-aware layout functions that accept `theme` and surface: header rect, rail rect, now_playing rect, controls rect, queue rect, footer/progress rect.
   - Store hitboxes with action keys; ensure min touch size ≥ `theme.touch_min_px`.

4) **Drawing Helpers**
   - Add helpers for pills/rounded rects using `radius_lg/radius_sm`.
   - Marquee text helper honoring `theme.mono_font` for timers/counters and `theme.base_font` for labels.
   - VU/progress bars: thickness = `progress_height`; volume bar width = `volume_width`.

5) **Config/Env Hook**
   - Respect `ui_theme` in existing config (`src/core/config_v2.py`) when present; env overrides config.
   - On missing/invalid theme JSON, log warning and fall back to default.

6) **Samples & Validation**
   - Add README blurb (already added) and ensure `docs/LCARS_THEME_PLAN.md` stays aligned.
   - Manual smoke: start with each sample theme (`lcars_default`, `lcars_rpi`, `lcars_ha`), verify bg/accents/buttons change, hitboxes OK, text readable.

7) **Service Path**
   - If running via systemd, ensure `WorkingDirectory` has access to `themes/` or copy themes to a known path; optionally allow `DFPLAYER_THEME_DIR` override.

## Nice-to-haves (optional after MVP)
- Live theme switcher (long-press or settings screen) that reloads theme and recalculates layout.
- Ship a “retro” palette matching the Winamp-style reference.
- Cache loaded fonts per `theme.base_font`/`theme.mono_font` to avoid repeated disk I/O.
