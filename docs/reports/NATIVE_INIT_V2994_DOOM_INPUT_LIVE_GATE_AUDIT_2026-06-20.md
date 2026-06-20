# Native Init V2994 DOOM Input Live Gate Audit

## Summary

- Decision: `v2994-doom-input-live-gate-not-actionable`
- Device action: `none` in this host-only/read-only unit.
- Track: active Video playback / DOOM input prerequisite.
- Resident build: `v2321-usb-clean-identity-rodata`
- Resident selftest fail=0: `1`
- V2992 keyboard fallback staged: `1`
- V2991 A90 keyboard candidates: `0`
- Host USB HID interfaces visible: `5`
- A90 USB peripheral/control present: `1`
- V2992 live ready now: `0`

## Gate Reasons

- No keyboard-class event has been observed on A90 inputscan evidence.
- Host USB HID devices are present, but they are host peripherals, not A90 evdev nodes.
- A90 is currently enumerated as a USB CDC gadget/peripheral for control.

## Next Action

- Run V2992 live only after A90 inputscan evidence can show a keyboard-class event, or after an operator-attached OTG path preserves control and keypress sampling.

## Evidence Inputs

- V2991 result: `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/result.json`
- V2992 report: `docs/reports/NATIVE_INIT_V2992_DOOMINPUT_KEYBOARD_STATE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md`
- V2993 report: `docs/reports/NATIVE_INIT_V2993_DOOM_INPUT_FRONTIER_DECISION_2026-06-20.md`
- Private raw outputs: `workspace/private/runs/input/v2994-doom-input-live-gate-20260620-183757`

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_live_gate_v2994.py tests/test_native_doom_input_live_gate_v2994.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_live_gate_v2994`: PASS (`5` tests)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_live_gate_v2994.py`: PASS (host-only/read-only report materialized)
- `git diff --check`: PASS

## Safety

- Host-only/read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.
- `a90ctl version`, `status`, and `selftest verbose` were read-only health checks on the resident v2321 image.
- `lsusb -t` was host topology inspection only; host HID devices were not treated as A90 input evidence.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
