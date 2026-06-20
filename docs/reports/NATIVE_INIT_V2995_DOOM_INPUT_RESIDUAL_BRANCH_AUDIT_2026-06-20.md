# Native Init V2995 DOOM Input Residual Branch Audit

## Summary

- Decision: `v2995-doom-input-residual-branches-gated`
- Device action: `none` in this host-only/source audit.
- Track: active Video playback / DOOM input prerequisite.
- Touch repeat branch: `gated-new-touch-hypothesis-required`
- USB keyboard branch: `gated-a90-keyboard-evdev-required`
- Physical button branch: `not-current-doom-fallback`
- Physical button viable as current DOOM fallback: `0`

## Evidence State

- V2991 keyboard candidates: `0` events: -
- V2991 touch candidates: `2` events: `event8` `sec_touchpad` class=`touch`, `event6` `sec_touchscreen` class=`touch`
- V2991 zero-event touch samples: `event6,event8`
- V2991 button candidates: `2` events: `event3` `gpio_keys` class=`buttons`, `event0` `qpnp_pon` class=`buttons`
- V2991 rollback clean: `1`
- V2993 touch repeat saturated: `1`
- V2994 keyboard live not actionable: `1`

## Source Audit

- Existing menu/input physical buttons: `KEY_POWER,KEY_VOLUMEDOWN,KEY_VOLUMEUP`
- `doominput_apply_key()` mapped keys: `BTN_TOUCH,KEY_A,KEY_D,KEY_DOWN,KEY_ENTER,KEY_ESC,KEY_LEFT,KEY_LEFTCTRL,KEY_LEFTSHIFT,KEY_RIGHT,KEY_RIGHTCTRL,KEY_RIGHTSHIFT,KEY_S,KEY_SPACE,KEY_UP,KEY_W`
- Device physical buttons mapped by current `doominput`: `-`
- The current `inputscan` classifier treats `KEY_POWER`/`KEY_VOLUMEUP`/`KEY_VOLUMEDOWN` as `buttons`, not `keyboard`.
- The current `doominput` state only treats WASD/arrows, Enter/Space, Esc, Ctrl/Shift, and touch contact as DOOM controls.

## Decision

- Repeating touch samples is gated by V2993 until a new touch hypothesis exists.
- Running V2992 keyboard live is gated by V2994 until A90 exposes a keyboard-class evdev node.
- Sampling `event0`/`event3` physical buttons through current `doominput` would not prove the requested USB-keyboard fallback because those keys are not mapped to DOOM state bits.
- A physical-button DOOM branch would require an explicit source design/change first; it is not a current live-validation branch.

## Next Action

- Do not flash another input live run for touch, USB keyboard, or physical buttons until the missing prerequisite changes: a new touch hypothesis, an A90 keyboard-class evdev node, or an explicit source change that defines a DOOM-capable physical-button map.

## Evidence Inputs

- V2991 result: `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/result.json`
- V2993 report: `docs/reports/NATIVE_INIT_V2993_DOOM_INPUT_FRONTIER_DECISION_2026-06-20.md`
- V2994 report: `docs/reports/NATIVE_INIT_V2994_DOOM_INPUT_LIVE_GATE_AUDIT_2026-06-20.md`
- Native menu/input source: `workspace/public/src/native-init/v319/40_menu_apps.inc.c`
- Native physical-button source: `workspace/public/src/native-init/a90_input.c`

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_residual_branch_audit_v2995.py tests/test_native_doom_input_residual_branch_audit_v2995.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_residual_branch_audit_v2995`: PASS (`5` tests)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_residual_branch_audit_v2995.py`: PASS (host-only/source report materialized)
- `git diff --check`: PASS

## Safety

- Host-only/source audit; no flash, no serial command, no evdev open, no input injection, and no sysfs write.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- No new raw command output is collected; prior private run inputs remain under `workspace/private/runs/` and this report includes metadata only.
