# Native Init V2988 Readinput DOOM Decode Touch Live

## Summary

- Decision: `v2988-readinput-doom-decode-touch-decode-not-proven`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.64 (v2987-readinput-doom-decode)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2987_readinput_doom_decode.img`
- Candidate SHA256: `fc5d680be0b6575ea4650a4e84a2ee7f0620cc02693e77b5f4453f44f9ffad21`
- Private run dir: `workspace/private/runs/input/v2988-readinput-doom-decode-live-20260620-173333`
- Live execution: `1`
- Requested mode: `touch` selected_mode=`touch`

## Dry-Run Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `touch mode requires finger movement during the readinput window; keyboard mode requires USB keyboard/OTG attached and keys pressed`

## Evidence

- Candidate version ok: `1`
- Candidate selftest fail=0: `1`
- Inputscan rc: `0` keyboard_candidates=`0` touch_candidates=`2`
- Selected event: `event6` name=`sec_touchscreen` class=`touch`
- Inputcaps rc: `0` caps_ok=`1`
- `readinput` rc: `-110` timeout_ms=`45000`
- Decoded events: `0` touch_decoded=`0` doom_decoded=`0` doom_presses=`0`
- Candidate post-sample selftest fail=0: `1`

## Input Candidates

- touch `event8` `sec_touchpad` class=`touch`
- touch `event6` `sec_touchscreen` class=`touch`

## Captured Decoded Events

- none captured

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Post-run host recheck: resident version=`v2321-usb-clean-identity-rodata` selftest_fail0=`1`

## Interpretation

- V2988 live flashed the V2987 decoded `readinput` candidate, proved the candidate boots with `selftest fail=0`, selected `event6 sec_touchscreen`, and confirmed the event still exposes the required touch capability bits.
- The bounded `readinput event6 32 45000` window timed out with `0` numeric events and `0` decoded events, so V2987's decoded touch event path is still not live-proven.
- Rollback to `v2321-usb-clean-identity-rodata` succeeded and an additional host-side read-only version/selftest check confirmed the device is back on the clean rollback baseline with `selftest fail=0`.
- Next meaningful branch is either another live decoded sample with deliberate operator finger motion during the window, or a USB-keyboard/OTG fallback validation when a keyboard-class event appears.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
