# Native Init V3018 Frontier Selector V3017 Gameplay Loop

## Summary

- Decision: `v3018-frontier-selector-v3017-gameplay-loop-pass`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM capstone steering.
- Selector decision after update: `frontier-selector-actionable-unit-present`
- Selected track: `VIDEO`
- Selected reason: `doomgeneric-wad-feasibility-host-ready`
- Superseded blocker: `v3012-doom-input-live-precondition-current-hardware-wait`
- Current proof input: `docs/reports/NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md`

## Change

- `GOAL.md` now records V3014-V3017 as superseding the OTG-keyboard hardware wait for the next DOOM iteration.
- The frontier selector now reads the V3017 live report and prefers its current evidence over the stale V3008/V3012 external-hardware gate.
- When V3017 proves `doompad` state consumption plus rollback health, the selector marks `VIDEO / doom-capstone` as actionable with status `doomgeneric-wad-feasibility-host-ready`.

## Evidence

- V3017 decision marker present: `1`
- V3017 `video demo doom play 8` rc and marker pass: `1`
- V3017 player moved forward from serial doompad state: `1`
- V3017 rollback health version/selftest pass: `1`
- V3017 still not WAD-backed `doomgeneric`: `1`

## Rationale

- The pasted continuation file points at the older V2983 touch-diagnostic frontier, but the current repository state has already advanced through V3017.
- `GOAL.md` also still said DOOM was waiting on A90-side OTG keyboard hardware, which is no longer the current frontier after the serial `doompad` path was built and live-validated.
- The next safe unit is host-only `doomgeneric`/WAD feasibility and asset-policy work; no WAD-backed boot image should be flashed until source provenance, boot-size impact, bounded runtime controls, and rollback validation are pinned.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_init_frontier_select.py tests/test_native_init_frontier_select.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS (`19` tests)
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_init_frontier_select.py --json`: PASS (`selected_track=VIDEO`, `selected_reason=doomgeneric-wad-feasibility-host-ready`)
- `git diff --check`: PASS

## Safety

- Host-only steering/report/test change.
- No flash, serial command, evdev open, input injection, sysfs write, Wi-Fi action, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, WAD asset, or forbidden partition path is touched.
- Existing V3017 raw command output remains private under `workspace/private/runs/`; this report includes metadata only.
