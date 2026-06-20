# Native Init V2979 Readinput Touch Sample Handoff

## Summary

- Decision: `v2979-readinput-dry-run`
- Result before rollback: `0`
- Track: Video playback / DOOM input prerequisite.
- Candidate reused: `A90 Linux init 0.10.60 (v2977-inputscan-summary)`
- Candidate SHA256: `52a5d0329f8c42f360772e4541f77d31d4f3569e7e01aa086d17ed655a4349aa`
- Event under test: `event6` count=`16`
- Private run dir: `workspace/private/runs/input/v2979-readinput-touch-sample-20260620-143459`

## Evidence

- Candidate version ok: `0`
- Candidate selftest fail=0: `0`
- `inputscan <event>` rc: `None` touch_class=`0`
- `readinput` rc: `None` cancel_sent=`0`
- Read events: `0` abs=`0` key=`0` syn=`0`
- Touch signal: `0` touch_abs=`0` btn_touch=`0`
- Candidate post-sample selftest fail=0: `0`

## Captured Event Sample

- none captured

## Inputscan Recheck

- Summary found: `0` events=`0` touch_candidates=`0`

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- This unit is the first bounded bridge between static input inventory and an actual evdev sample for the DOOM prerequisite.
- A pass proves the selected touch event emits EV_ABS/BTN_TOUCH-class data through native init without input injection or configuration writes.
- If the sample window times out, the runner sends `q` and records a cancelled run rather than leaving a blocking command active.

## Safety

- Only the boot partition is flashed, through `native_init_flash.py`; rollback target is `v2321`.
- The live path only opens and reads the selected `/dev/input/event*` node through `readinput`; no input injection, keymap writes, Wi-Fi, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes only event metadata.
