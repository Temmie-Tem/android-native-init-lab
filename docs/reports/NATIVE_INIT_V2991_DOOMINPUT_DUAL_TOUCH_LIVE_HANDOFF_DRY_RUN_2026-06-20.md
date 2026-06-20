# Native Init V2991 DOOM Dual Touch State Touch Live

## Summary

- Decision: `v2991-doominput-dual-touch-touch-state-not-proven`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate reused: `A90 Linux init 0.10.65 (v2989-doominput-state)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img`
- Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`
- Events: `event6,event8`
- Private run dir: `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451`
- Live execution: `1`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `operator finger movement during each bounded doominput touch window`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Inputscan rc: `0` touch_candidates=`2`
- Candidate post-sample selftest fail=0: `1`

## Touch Candidates

- touch `event8` `sec_touchpad` class=`touch`
- touch `event6` `sec_touchscreen` class=`touch`

## Per-Event Results

- `event6` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0` touch_states=`0` pass=`0`
- `event8` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0` touch_states=`0` pass=`0`

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Post-run host recheck: resident version=`v2321-usb-clean-identity-rodata` selftest_fail0=`1`

## Interpretation

- V2991 live flashed the V2989 `doominput` state candidate and sampled both known MT-capable touch nodes in one candidate boot.
- Both `event6 sec_touchscreen` and `event8 sec_touchpad` were still selected as touch-class nodes with touch capability bits, but both bounded `doominput <event> 32 45000` windows timed out with `captured=0/32`.
- No `doominput.event` or `doominput.state` lines were captured from either touch node, so the V2989 touch-state path remains not live-proven.
- Candidate health stayed clean after the samples, rollback to `v2321-usb-clean-identity-rodata` succeeded, and a post-run host version/selftest check confirmed resident `v2321` with `selftest fail=0`.
- With both built-in touch nodes producing zero evdev events in this bounded live pass, the next meaningful branch is the USB-keyboard/OTG fallback when a keyboard-class event appears, or a new touch hypothesis backed by fresh evidence. Do not keep re-running identical touch samples without a deliberate operator/input-state change.

## Host Validation

- Pre-live host check: `version` showed `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`; `selftest verbose` returned `fail=0`.
- Live runner: `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_dual_touch_live_handoff_v2991.py --live --events event6,event8 --count 32 --timeout-ms 45000`: completed with expected non-pass result `v2991-doominput-dual-touch-touch-state-not-proven`; rollback health version/selftest passed.
- Post-live host check: `version` again showed `v2321-usb-clean-identity-rodata`; `selftest verbose` returned `fail=0`.
- Raw `doominput` outputs remain private at `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/09_candidate-doominput-event6-touch-state-sample.txt` and `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181451/13_candidate-doominput-event8-touch-state-sample.txt`.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
