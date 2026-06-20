# Native Init V2978 Inputscan Live Validation

## Summary

- Decision: `v2978-inputscan-live-pass-before-rollback`
- Result before rollback: `1`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.60 (v2977-inputscan-summary)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2977_inputscan_summary.img`
- Candidate SHA256: `52a5d0329f8c42f360772e4541f77d31d4f3569e7e01aa086d17ed655a4349aa`
- Private run dir: `workspace/private/runs/input/v2978-inputscan-live-20260620-141918`
- Reclassified from existing live evidence: `1`

## Live Evidence

- Candidate version ok: `1`
- Candidate status ok: `1`
- Candidate selftest fail=0: `1`
- Inputscan rc: `0`
- Input events: `9` nodes=`9`
- Touch candidates: `2`
- Keyboard candidates: `0`
- Button candidates: `2`
- Candidate post-scan selftest fail=0: `1`

## Touch Candidates

- `event8` `sec_touchpad` class=`touch`
- `event6` `sec_touchscreen` class=`touch`

## Keyboard Fallback Candidates

- none captured in this run

## Rollback Evidence

- Rollback attempted: `1`
- Rollback step ok: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Interpretation

- V2978 validates the V2977 `inputscan` command on hardware without consuming input events or requiring a human touch sample.
- If touch candidates are present, the next bounded unit can sample the named event with `readinput <event> 1` while the operator touches the panel.
- If no touch candidate is present but keyboard candidates exist, DOOM input should pivot to the USB-keyboard fallback before touch firmware work.

## Safety

- Only the boot partition was flashed, through `native_init_flash.py`; rollback target remained `v2321`.
- No input stream read, input injection, keymap change, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path was touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes only metadata and event names/classes.
