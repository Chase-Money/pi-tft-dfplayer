# Coding Standards (AI & Devs)

- Python 3.9+, 4-space indent; constants in SCREAMING_SNAKE_CASE.
- Small, single-purpose functions; keep hardware access wrapped in try/except.
- UI: use the v2 framework/components; no new ad-hoc `_v2` forks or monolith expansions.
- Touch: handle ABS/BTN batches, honor calibration/orientation, thresholds configurable (tap ~400ms, drag ~12px, swipe ~48px).
- DFPlayer/backends: avoid side effects in helpers; log and degrade gracefully on UART failures.
- Theming: load via `DFPLAYER_THEME`/`themes/*.json`; no hardcoded palettes where theme is plumbed.
- Git: feature branches only; keep `main` stable; no destructive commands.
