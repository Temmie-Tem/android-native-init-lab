# Native Init V3007 DOOM Keyboard Gate Current Audit

## Summary

- Decision: `v3007-doom-keyboard-gate-hardware-stimulus-required`
- Device action: `none` in this read-only unit.
- Track: active Video playback / DOOM input prerequisite.
- Resident build: `v2321-usb-clean-identity-rodata`
- Resident selftest fail=0: `1`
- V3004 keyboard gate preflight ok: `1`
- V3004 live already executed: `0`
- V3006 status surface live pass: `1`
- V3006 status points to V3004 gate: `1`
- Host USB HID interfaces visible: `5`
- A90 USB control/peripheral present: `1`
- A90 OTG keyboard evdev evidence: `0`
- V3004 live actionable now: `0`

## Gate Reasons

- Host HID interfaces are visible, but they are not A90 OTG evdev keyboard evidence.
- A90 is currently present as a USB control/peripheral path, not proven OTG keyboard host.
- No current evidence shows an attached A90 USB keyboard/OTG path with operator key presses available.

## Next Action

- Run V3004 live only when USB keyboard/OTG is attached to the A90, the serial/control path remains available, and an operator can press DOOM keys during the bounded `doominput` window.

## Evidence Inputs

- V3004 report: `docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md`
- V3006 report: `docs/reports/NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md`
- Private raw outputs: `workspace/private/runs/input/v3007-doom-keyboard-gate-current-audit-20260620-201052`

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_keyboard_gate_current_audit_v3007.py tests/test_native_doom_keyboard_gate_current_audit_v3007.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_keyboard_gate_current_audit_v3007`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_keyboard_gate_current_audit_v3007.py`: PASS (read-only report materialized)
- `git diff --check`: PASS

## Safety

- Read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.
- `a90ctl version`, `status`, and `selftest verbose` are read-only health checks on the resident rollback image.
- `lsusb -t` is host topology inspection only; host HID devices are not treated as A90 input evidence.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
