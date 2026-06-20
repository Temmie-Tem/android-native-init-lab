# Native Init V2990 DOOM Input State Touch Live

## Summary

- Decision: `v2990-doominput-state-touch-state-not-proven`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.65 (v2989-doominput-state)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img`
- Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`
- Private run dir: `workspace/private/runs/input/v2990-doominput-state-live-20260620-180202`
- Live execution: `1`
- Requested mode: `touch` selected_mode=`touch`

## Dry-Run Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `touch mode requires finger movement during the doominput window; keyboard mode requires USB keyboard/OTG attached and keys pressed`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Inputscan rc: `0` keyboard_candidates=`0` touch_candidates=`2`
- Selected event: `event6` name=`sec_touchscreen` class=`touch`
- Inputcaps rc: `0` caps_ok=`1`
- `doominput` rc: `-110` timeout_ms=`45000`
- DOOM input events: `0` states=`0` touch_states=`0` active_states=`0` doom_button_states=`0` max_frame=`None`
- Candidate post-sample selftest fail=0: `1`

## Input Candidates

- touch `event8` `sec_touchpad` class=`touch`
- touch `event6` `sec_touchscreen` class=`touch`

## Captured DOOM Input State

- none captured

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Post-run host recheck: resident version=`v2321-usb-clean-identity-rodata` selftest_fail0=`1`

## Interpretation

- V2990 live flashed the V2989 `doominput` state candidate, proved the candidate boots with `selftest fail=0`, selected `event6 sec_touchscreen`, and confirmed the event still exposes the required touch capability bits.
- The bounded `doominput event6 32 45000` window timed out with `captured=0/32`, `0` `doominput.event` lines, and `0` `doominput.state` lines, so the V2989 touch-state surface is not yet live-proven.
- Rollback to `v2321-usb-clean-identity-rodata` succeeded, and an additional host-side read-only version/selftest check confirmed the device is back on the clean rollback baseline with `selftest fail=0`.
- Next meaningful branch is either an `event8` touch-state live sample with deliberate operator finger motion, or a USB-keyboard/OTG fallback validation when a keyboard-class event appears.

## Host Validation

- Pre-live host check: `version` showed `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`; `selftest verbose` returned `fail=0`.
- Live runner: `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_state_live_handoff_v2990.py --live --mode touch --event event6 --count 32 --timeout-ms 45000`: completed with expected non-pass result `v2990-doominput-state-touch-state-not-proven`; rollback health version/selftest passed.
- Post-live host check: `version` again showed `v2321-usb-clean-identity-rodata`; `selftest verbose` returned `fail=0`.
- Raw `doominput` output remains private at `workspace/private/runs/input/v2990-doominput-state-live-20260620-180202/09_candidate-doominput-touch-state-sample.txt`.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
