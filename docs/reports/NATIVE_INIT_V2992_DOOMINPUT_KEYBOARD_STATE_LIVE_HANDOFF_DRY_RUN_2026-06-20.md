# Native Init V2992 DOOM Input Keyboard State Live Handoff Dry Run

## Summary

- Decision: `v2992-doominput-keyboard-state-dry-run`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate reused: `A90 Linux init 0.10.65 (v2989-doominput-state)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img`
- Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`
- Private run dir: `workspace/private/runs/input/v2992-doominput-keyboard-state-live-20260620-182629`
- Live execution: `0`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `USB keyboard/OTG attached and DOOM keys pressed during the doominput window`

## Evidence

- Candidate version ok: `not-run`
- Candidate selftest fail=0: `not-run`
- Inputscan rc: `not-run` keyboard_candidates=`not-run`
- Selected event: `-` name=`-` class=`-`
- Inputcaps rc: `not-run` caps_ok=`not-run`
- `doominput` rc: `not-run` timeout_ms=`not-run`
- DOOM input events: `not-run` states=`not-run` doom_button_states=`not-run` active_states=`not-run`
- Candidate post-sample selftest fail=0: `not-run`

## Keyboard Candidates

- none captured in this run

## Captured DOOM Button State

- none captured

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- V2992 stages the USB-keyboard/OTG fallback on the current V2989 `doominput.state` candidate after both built-in touch nodes produced zero events.
- Pass requires a keyboard-class evdev node, DOOM-relevant key capability bits, and at least one active DOOM button state from `doominput.state`.
- Dry-run mode does not flash; live mode should run only when a USB keyboard/OTG path is attached and keys are pressed during the bounded sample window.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doominput_keyboard_state_live_handoff_v2992.py tests/test_native_doominput_keyboard_state_live_handoff_v2992.py`: PASS.
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_keyboard_state_live_handoff_v2992`: PASS (`6` tests).
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_keyboard_state_live_handoff_v2992.py --count 32 --timeout-ms 45000`: PASS, dry-run preflight ok `1`, no flash.
- `git diff --check`: PASS.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
