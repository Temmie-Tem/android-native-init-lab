# Native Init V2988 Readinput DOOM Decode Live Handoff Dry Run

## Summary

- Decision: `v2988-readinput-doom-decode-dry-run`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.64 (v2987-readinput-doom-decode)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2987_readinput_doom_decode.img`
- Candidate SHA256: `fc5d680be0b6575ea4650a4e84a2ee7f0620cc02693e77b5f4453f44f9ffad21`
- Private run dir: `workspace/private/runs/input/v2988-readinput-doom-decode-live-20260620-173001`
- Live execution: `0`
- Requested mode: `auto` selected_mode=`-`

## Dry-Run Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `touch mode requires finger movement during the readinput window; keyboard mode requires USB keyboard/OTG attached and keys pressed`

## Evidence

- Candidate version ok: `not-run`
- Candidate selftest fail=0: `not-run`
- Inputscan rc: `not-run` keyboard_candidates=`not-run` touch_candidates=`not-run`
- Selected event: `-` name=`-` class=`-`
- Inputcaps rc: `not-run` caps_ok=`not-run`
- `readinput` rc: `not-run` timeout_ms=`not-run`
- Decoded events: `not-run` touch_decoded=`not-run` doom_decoded=`not-run` doom_presses=`not-run`
- Candidate post-sample selftest fail=0: `not-run`

## Input Candidates

- none captured in this run

## Captured Decoded Events

- none captured

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- V2988 stages the live handoff for the V2987 decoded readinput candidate, covering both proven MT-capable touch nodes and the USB-keyboard fallback.
- Pass requires the decoded `event.decode` line to carry either touch roles (`touch_x`/`touch_y`/`touch_tracking`/`touch_contact`) or a pressed DOOM keyboard role (`doom_*`), plus clean rollback health.
- This dry run intentionally does not flash because meaningful validation still needs operator finger motion or an attached USB keyboard during the bounded read window.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
