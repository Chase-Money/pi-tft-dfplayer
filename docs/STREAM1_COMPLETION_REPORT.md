# Stream 2 (Dev A) Progress Report (Legacy)
Legacy progress report. Track new stream progress in `docs/ai/TASK_LOG.md` and align with `docs/ai/PROJECT_GUIDE.md`.

## What was delivered
- Calibration & Settings screens added to the v2 UI stack:
  - `src/ui/screens_v2/calibration.py` implements four-point calibration using raw driver coords, inverts orientation, and persists bounds to config via `set_touch_calibration`.
  - `src/ui/screens_v2/settings.py` surfaces orientation cycling (all 8 modes) and a shortcut into calibration.
- UI polish:
  - Status banners across Home/Track Browser/Now Playing; artwork placeholder when absent; button flash feedback; slider easing; drag scrolling in Track Browser with hysteresis/guard rails.
- Core touch/config hookup:
  - `src/main_tft_v2.py` now respects config orientation/calibration, exposes status messages to screens, and normalized imports to package-relative paths.
- Desktop-freeing helper:
  - `scripts/disable_desktop_and_free_fb1.sh` to disable lightdm or force HDMI-only desktop so `/dev/fb1` stays free for the framebuffer app. Documented in README.

## How to validate on-device
1) Free fb1 from the desktop (if you’re seeing the Raspberry Pi Desktop on the TFT):
   - `sudo ./scripts/disable_desktop_and_free_fb1.sh tft-only` (or `hdmi` to keep desktop on HDMI) then reboot.
2) Launch the v2 TFT app:
   - `sudo -E DFPLAYER_UI_FRAMEWORK=1 python3 src/main_tft_v2.py`
3) Open Home → Settings:
   - Cycle orientations and confirm touch mapping updates.
   - Run Calibration; tap all four targets; verify touch accuracy afterward.
4) From Home, browse tracks and play; ensure status banners reflect backend availability.

## Known gaps / next steps
- Stream 1/3 dependencies still open: real config_v2, backend shutdown alias, dirty-rect rendering, and more tests from Streams 1/3.
- Touch events in `TouchController` now carry raw coords; ensure downstream widgets keep using `pos` payloads (already standardized in v2 code).
- Continue hardware validation after freeing fb1; if X11 is still grabbing fb1, use the helper script or move the desktop to HDMI.
