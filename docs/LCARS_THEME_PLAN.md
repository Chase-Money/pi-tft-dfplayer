# LCARS + Retro Player UI Plan & Theming Schema

Goal: combine LCARS panels (pill edges, saturated bars, minimal shading) with retro MP3 player cues (bezelled art, readable tags) while enabling user-defined themes.

## Style Guide (defaults)
- Background: `#0c0c10` with beige panel fills `#f5e9d7`.
- Accents: amber `#f2b84b`, coral `#f47e6a`, plum `#7e5ba6`, teal `#3ab6c5`, steel `#7fa3d9`.
- Text: light `#f0f0f5`, dim `#5a606e`.
- Metrics: large radius 24–28px for bands/buttons, small radius 8px for inner cards, stroke 2px, padding 12px, gaps 8px. Touch targets ≥44px.
- Type: Title/labels in square mono (e.g., Share Tech Mono / JetBrains Mono). Body in rounded sans (e.g., Nunito / Atkinson Hyperlegible).

## Layout Sketches
Landscape:
```
[VOL] | HEADER: System/Clock ---------------------------------------------|
      |                                                                   |
      | Art [####]  Title/Artist bars   | Transport pills                 |
      |            VU ticks             | [Prev][Play/Pause][Next][Stop]  |
      |                                 | Progress ====o====  t1     t2   |
      |                                 | Repeat/Shuffle tags; status     |
      | Queue: > Track A / Track B                                        |
-------------------------------------------------------------------------|
```

Portrait:
```
HEADER: System/Clock
Art [####] Title/Artist bars
VU ticks
Progress ====o==== t1 t2
Transport [Prev][Play/Pause][Next][Stop]  Repeat/Shuffle
Volume swoop on right edge
Queue: > Track A / Track B
```

## Theming Engine (user-extensible)
- Themes live in `themes/*.json`; selected via `DFPLAYER_THEME` env or config key `ui_theme`.
- Schema fields:
  - `name`, `description`, `base_font`, `mono_font`.
  - `palette`: `bg`, `panel`, `text`, `text_dim`, `accents` (array), `status_good`, `status_warn`, `status_bad`.
  - `metrics`: `radius_lg`, `radius_sm`, `stroke`, `padding`, `gap`, `touch_min`.
  - `layout`: optional overrides per module: `header_color`, `rail_color`, `button_primary`, `button_secondary`, `progress_height`, `volume_width`, `accent_cycle`.
- On load: validate keys, clamp values, fall back to defaults; log warnings instead of crashing.
- Future: hot-switch themes via long-press button or settings view.

### Example `themes/lcars_default.json`
```json
{
  "name": "LCARS Default",
  "description": "LCARS bands with retro player cues",
  "base_font": "Nunito",
  "mono_font": "ShareTechMono",
  "palette": {
    "bg": "#0c0c10",
    "panel": "#f5e9d7",
    "text": "#f0f0f5",
    "text_dim": "#5a606e",
    "accents": ["#f2b84b", "#f47e6a", "#7e5ba6", "#3ab6c5", "#7fa3d9"],
    "status_good": "#3ab6c5",
    "status_warn": "#f2b84b",
    "status_bad": "#f47e6a"
  },
  "metrics": {
    "radius_lg": 24,
    "radius_sm": 8,
    "stroke": 2,
    "padding": 12,
    "gap": 8,
    "touch_min": 44
  },
  "layout": {
    "header_color": "#7fa3d9",
    "rail_color": "#7e5ba6",
    "button_primary": "#f2b84b",
    "button_secondary": "#f5e9d7",
    "progress_height": 10,
    "volume_width": 22,
    "accent_cycle": ["bg", "panel", "accents[0]", "accents[1]"]
  }
}
```

## Implementation Steps (phased)
1) **Theme primitives**: dataclass + loader (default to LCARS if missing). Helpers: hex→RGB, clamp, metrics defaults.
2) **Layout scaffold**: header/rail/footer rect calculator for landscape/portrait; store button hitboxes alongside.
3) **Module rev**: art bezel + metadata bars + VU ticks; transport pills + progress; volume swoop + queue styling.
4) **Status + motion**: lightweight VU/progress tickers (coarse update), press feedback brightness bump.
5) **Docs & samples**: document schema in README; ship LCARS and retro sample JSON; note `DFPLAYER_THEME` usage.

## Manual Validation (per release)
- Verify theme load fallback when JSON missing/invalid.
- Check touch targets ≥44px and correct hitboxes after orientation swap.
- Test volume/transport taps and progress ticks for responsiveness on Pi.
- Confirm artwork/metadata updates do not block UI; marquee scrolls without ghosting.

## Sample Themes (current set)
- `themes/lcars_default.json`: LCARS + retro player accents (baked-in default).
- `themes/lcars_rpi.json`: Colors from tobykurien/rpi_lcars pygame demo.
- `themes/lcars_ha.json`: Colors from th3jesta/ha-lcars Home Assistant theme.
