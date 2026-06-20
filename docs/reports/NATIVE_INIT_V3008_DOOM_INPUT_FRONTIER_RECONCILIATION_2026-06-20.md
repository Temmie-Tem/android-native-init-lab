# Native Init V3008 DOOM Input Frontier Reconciliation

## Summary

- Decision: `v3008-doom-input-frontier-keyboard-gate-still-external-stimulus`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM input prerequisite.
- Touch capability/runtime-PM branch closed: `1`
- Touch event liveness still not proven: `1`
- Physical-button mux liveness still not proven: `1`
- USB keyboard live gate staged: `1`
- Status surface points to USB keyboard gate: `1`
- Current V3007 gate actionable now: `0`
- Active tier saturated without external stimulus: `1`

## Reconciled Evidence

- V2984: touch/MT capability bits are present on `event6` and `event8`; runtime-PM is `unsupported`, not `suspended` (`docs/reports/NATIVE_INIT_V2984_INPUTCAPS_TOUCH_DIAG_LIVE_2026-06-20.md`).
- V2990/V2991: `doominput` touch samples on `event6` and `event8` still captured zero events/states (`docs/reports/NATIVE_INIT_V2990_DOOMINPUT_STATE_LIVE_HANDOFF_DRY_RUN_2026-06-20.md`, `docs/reports/NATIVE_INIT_V2991_DOOMINPUT_DUAL_TOUCH_LIVE_HANDOFF_DRY_RUN_2026-06-20.md`).
- V3002/V3003: physical-button mux capability exists, but the bounded mux run captured zero events/states, so repeating it without confirmed button input is low-information (`docs/reports/NATIVE_INIT_V3002_DOOMINPUT_MUX_LIVE_2026-06-20.md`).
- V3004: the higher-information USB keyboard/OTG gate is staged and preflight-clean, but has not run live (`docs/reports/NATIVE_INIT_V3004_DOOMINPUT_KEYBOARD_LIVE_GATE_DRY_RUN_2026-06-20.md`).
- V3006/V3007: device-visible DOOM status points to V3004, and the current gate audit records no A90 OTG keyboard evdev evidence (`docs/reports/NATIVE_INIT_V3006_DOOM_KEYBOARD_GATE_STATUS_LIVE_2026-06-20.md`, `docs/reports/NATIVE_INIT_V3007_DOOM_KEYBOARD_GATE_CURRENT_AUDIT_2026-06-20.md`).

## Drop-Tier Trigger

- Active DOOM input tier needs external hardware stimulus that is not currently evidenced; host-only reconciliation records the trigger instead of re-flashing a low-information sample.

## Next Live Action

- Do not repeat touch, physical-button mux, or keyboard live flashes until a real input-state change is present. The next live action is V3004 with USB keyboard/OTG attached to the A90 and operator DOOM key presses during the bounded window.
- Command when the external prerequisite is true: `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000`

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_frontier_reconcile_v3008.py tests/test_native_doom_input_frontier_reconcile_v3008.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_frontier_reconcile_v3008`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_frontier_reconcile_v3008.py`: PASS (host-only report materialized)
- `git diff --check`: PASS

## Safety

- Host-only metadata reconciliation; no flash, no serial command, no evdev open, no input injection, and no sysfs write.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- No private raw logs or device identifiers are copied into this report.
