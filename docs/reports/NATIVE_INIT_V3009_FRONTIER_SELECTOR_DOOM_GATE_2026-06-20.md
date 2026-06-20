# Native Init V3009 Frontier Selector DOOM Gate

## Summary

- Decision: `v3009-frontier-selector-current-doom-gate-pass`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM input prerequisite plus T3 tooling hardening.
- Selector decision: `frontier-selector-no-automatic-safe-unit`
- First evaluated track: `VIDEO` / `doom-input`
- First track status: `external-hardware-stimulus-required`
- First track safe actionable now: `0`
- Next live gate retained: `native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000`

## Change

- `native_init_frontier_select.py` now reads the current V3008 DOOM input reconciliation report when present.
- The selector emits a first-class `VIDEO` / `doom-input` evaluation before the older T1/T2/T3 backlog checks.
- When V3008 records the external-stimulus gate, the selector's next decision tells the loop to attach USB keyboard/OTG and press DOOM keys before running V3004, otherwise use only T3 host-only tooling and do not repeat touch/button live flashes.

## Rationale

- V3008 records that touch capability/runtime-PM is no longer the open question, built-in touch and physical-button liveness remain unproven, and the higher-information gate is USB keyboard/OTG.
- The selector previously reflected older kernel/WLAN cleanup state and could not surface the current active Video/DOOM blocker.
- This is tooling hardening, not a new live attempt: it reduces the chance that stale context causes a low-information flash.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_init_frontier_select.py tests/test_native_init_frontier_select.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS (10 tests)
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_init_frontier_select.py --json`: PASS
- `git diff --check`: PASS

## Safety

- Host-only selector/test/report change.
- No flash, no serial command, no evdev open, no input injection, no sysfs write.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
