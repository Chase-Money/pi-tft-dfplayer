# Button Reference — Waveshare 1.44" Variant

BCM Pins
- KEY1: 21 (top)
- KEY2: 20 (middle)
- KEY3: 16 (bottom)
- Joystick UP/DOWN/LEFT/RIGHT: 6 / 19 / 5 / 26
- Joystick PRESS (center): 13

Default Mapping (proposed)
- KEY1: Play/Pause (HOLD = Next Track)
- KEY2: Stop (HOLD = Previous Track)
- KEY3: Menu (HOLD = Alphabet Jump)
- Joystick UP/DOWN: Navigate list (HOLD = jump by letter)
- Joystick LEFT/RIGHT: Volume down/up
- Joystick PRESS: Select/Confirm

Event Semantics
- PRESS fires on the down edge.
- HOLD fires after 350 ms; when HOLD fires, PRESS for the same cycle is suppressed (no double‑fire).
- RELEASE always fires on the up edge.

