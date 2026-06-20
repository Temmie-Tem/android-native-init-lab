# Native Init V3012 DOOM Input Live Precondition Current Audit

## Summary

- Decision: `v3012-doom-input-live-precondition-current-hardware-wait`
- Device action: `none` in this read-only unit.
- Track: active Video playback / DOOM input prerequisite plus T3 safety tooling.
- Bridge/control path ready: `1`
- Bridge probe ok: `1`
- Resident build: `v2321-usb-clean-identity-rodata`
- Resident selftest fail=0: `1`
- V3010 flash-gate assets ready: `1`
- V3011 selector external gate retained: `1`
- Host USB HID interfaces visible: `5`
- Host CDC interfaces visible: `6`
- A90 OTG keyboard evdev evidence: `0`
- V3004 live actionable now: `0`

## Gate Reasons

- Resident V2321 control path and selftest are clean.
- V3010/V3011 report and selector evidence show the V3004 live-gate assets are ready.
- The selector still classifies DOOM input as external-hardware-stimulus-required.
- Host HID interfaces are visible, but they are not A90 OTG evdev keyboard evidence.
- No current evidence shows an A90-side OTG keyboard evdev path plus operator DOOM key presses.

## Selector And Report Inputs

- V3008 external gate marker: `1`
- V3010 assets marker: `1`
- V3010 reports-ok marker: `1`
- V3011 selector pass marker: `1`
- Selector decision: `frontier-selector-no-automatic-safe-unit`
- Selector first track/status: `VIDEO` / `external-hardware-stimulus-required`
- Command when the external prerequisite is true: `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000`

## Evidence Inputs

- V3008 report: `docs/reports/NATIVE_INIT_V3008_DOOM_INPUT_FRONTIER_RECONCILIATION_2026-06-20.md`
- V3010 report: `docs/reports/NATIVE_INIT_V3010_DOOM_INPUT_FLASH_GATE_ASSETS_2026-06-20.md`
- V3011 report: `docs/reports/NATIVE_INIT_V3011_FRONTIER_SELECTOR_V3010_ASSETS_2026-06-20.md`
- Private raw outputs: `workspace/private/runs/input/v3012-doom-input-live-precondition-current-20260620-204227`

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_live_precondition_current_v3012.py tests/test_native_doom_input_live_precondition_current_v3012.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_live_precondition_current_v3012`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_live_precondition_current_v3012.py`: PASS (read-only report materialized)
- `git diff --check`: PASS

## Safety

- Read-only audit; no flash, no build artifact, no evdev open, no input injection, and no sysfs write.
- `a90_bridge status --json`, `a90ctl version`, `status`, and `selftest verbose` are read-only health checks on the resident rollback image.
- `lsusb -t` is host topology inspection only; host HID devices are not treated as A90 input evidence.
- The frontier selector is executed in read-only mode to reuse committed report evidence.
- No Wi-Fi scan/connect/DHCP/ping, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
