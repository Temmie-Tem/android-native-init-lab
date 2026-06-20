# Native Init V2986 DOOM Keyboard Live Handoff Dry Run

## Summary

- Decision: `v2986-doom-keyboard-dry-run`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.63 (v2985-doom-keyboard-caps)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2985_doom_keyboard_caps.img`
- Candidate SHA256: `4ffdb9b6078e99b3c5f40db42c0c9ef9d01f7936006be33943a65d9965343e54`
- Private run dir: `workspace/private/runs/input/v2986-doom-keyboard-live-20260620-171346`
- Live execution: `0`

## Dry-Run Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `USB keyboard/OTG attached and keys pressed during readinput window`

## Evidence

- Candidate version ok: `not-run`
- Candidate selftest fail=0: `not-run`
- Inputscan rc: `not-run` keyboard_candidates=`not-run`
- Selected event: `-` name=`-` class=`-`
- Inputcaps rc: `not-run` doom_caps_ok=`not-run`
- `readinput` rc: `not-run` timeout_ms=`not-run`
- Captured events: `not-run` key_events=`not-run` doom_key_events=`not-run`
- Candidate post-sample selftest fail=0: `not-run`

## Keyboard Candidates

- none captured in this run

## Captured DOOM Key Events

- none captured

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- V2986 stages the exact live handoff for the DOOM USB-keyboard fallback after V2984 showed touch capability/runtime-PM did not explain zero touch samples.
- Pass requires a keyboard-class evdev node, DOOM-relevant key capability bits, a bounded native `readinput` sample containing a DOOM key event, and clean rollback health.
- This dry run intentionally does not flash until a USB keyboard/OTG path is attached; current v2321 precheck observed only built-in input nodes (`event0` through `event8`).

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
