# Native Init V3015 DOOMPAD Serial Controller Live Validation

## Summary

- Decision: `v3015-doompad-serial-controller-serial-state-pass-before-rollback`
- Result before rollback: `1`
- Track: active Video playback / DOOM input handoff.
- Candidate: `A90 Linux init 0.10.70 (v3014-doompad-serial-controller)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3014_doompad_serial_controller.img`
- Candidate SHA256: `5bdcab90807fe03f1f97717e4b371bce6c3567ad1f7635b51babb77b83b61455`
- Private run dir: `workspace/private/runs/video/v3015-doompad-serial-controller-live-20260621-010532`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `none; serial doompad validation uses only the command bridge`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- `video status` rc: `0` markers_ok=`1`
- `video demo doom status` rc: `0` markers_ok=`1`
- `doompad` state sequence ok: `1`
- Candidate post-doompad selftest fail=0: `1`

## DOOMPAD Steps

| step | rc | markers_ok |
| --- | ---: | ---: |
| `doompad-fire-down` | `0` | `1` |
| `doompad-fire-up` | `0` | `1` |
| `doompad-forward-down` | `0` | `1` |
| `doompad-forward-up` | `0` | `1` |
| `doompad-reset` | `0` | `1` |
| `doompad-status-initial` | `0` | `1` |
| `doompad-use-tap` | `0` | `1` |

## Video Status Markers

- `video.status.doom_input=serial-doompad-staged`: `1`
- `video.status.doom_stub=1`: `1`

## DOOM Status Markers

- `video.demo.doom.status_rc=0`: `1`
- `video.demo.input.command=doompad key <role> <0|1>`: `1`
- `video.demo.input.hardware_gate=none-serial-control`: `1`
- `video.demo.input.virtual_controller=doompad-serial-v3014`: `1`
- `video.demo.input=serial-doompad-staged`: `1`
- `video.demo.preset=doom`: `1`
- `video.demo.status=blocked-gameplay-loop`: `1`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- V3015 validates that V3014 boots and exposes a serial-controlled in-memory DOOM input state.
- The pass condition is command-channel state handoff only; gameplay consumption is intentionally not wired in this unit.
- USB keyboard/OTG remains a fallback diagnostic path, not the primary proof path.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path uses status and `doompad` commands over the serial command bridge.
- No input injection, `uinput`, `EVIOCGRAB`, evdev read window, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py tests/test_native_doompad_serial_controller_live_v3015.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doompad_serial_controller_live_v3015`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py`: PASS (dry-run preflight/report)
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doompad_serial_controller_live_validation_v3015.py --live`: PASS (doompad state transitions and rollback v2321/selftest fail=0)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe selftest`: PASS (post-rollback `fail=0`)
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/a90ctl.py --retry-unsafe status`: PASS (post-rollback `v2321-usb-clean-identity-rodata`, `selftest fail=0`)
- `git diff --check`: PASS
