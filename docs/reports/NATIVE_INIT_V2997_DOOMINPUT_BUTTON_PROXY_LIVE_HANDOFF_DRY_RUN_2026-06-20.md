# Native Init V2997 DOOM Input Button Proxy Live Handoff Dry Run

## Summary

- Decision: `v2997-doominput-button-proxy-dry-run`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate: `A90 Linux init 0.10.66 (v2996-doominput-button-proxy)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2996_doominput_button_proxy.img`
- Candidate SHA256: `1509ce74701f2f8d30e7a5ee924b108ca9bb60debed8afab5f9352643e2a4a75`
- Events: `event3,event0`
- Private run dir: `workspace/private/runs/input/v2997-doominput-button-proxy-live-20260620-185857`
- Live execution: `0`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `operator presses VOLUMEUP/VOLUMEDOWN/POWER during each bounded doominput window`

## Evidence

- Candidate version ok: `not-run`
- Candidate selftest fail=0: `not-run`
- Inputscan rc: `not-run` button_candidates=`not-run`
- Candidate post-sample selftest fail=0: `not-run`

## Button Candidates

- none captured in this run

## Per-Event Results

- none captured in this run

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- V2997 stages live validation for the V2996 diagnostic physical-button proxy candidate.
- Pass requires a selected `buttons` event, POWER/VOLUME capability bits, and `doominput.state` evidence for `forward`, `back`, or `fire` while candidate health remains clean.
- Dry-run mode does not flash; live mode should run only when an operator can press A90 physical buttons during the bounded sample windows.
- This is diagnostic evdev-to-`doominput.state` liveness proof, not a final DOOM control scheme.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doominput_button_proxy_live_handoff_v2997.py tests/test_native_doominput_button_proxy_live_handoff_v2997.py`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_button_proxy_live_handoff_v2997`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_button_proxy_live_handoff_v2997.py --count 16 --timeout-ms 45000`: PASS (dry-run preflight/report)
- `git diff --check`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest discover -s tests -p 'test_*.py'`: FAIL (`25` failures, `5` errors in legacy audio tests; focused V2997 tests passed).
