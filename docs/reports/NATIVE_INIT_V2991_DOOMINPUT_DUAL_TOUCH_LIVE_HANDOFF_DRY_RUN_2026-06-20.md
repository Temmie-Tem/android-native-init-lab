# Native Init V2991 DOOM Dual Touch State Live Handoff Dry Run

## Summary

- Decision: `v2991-doominput-dual-touch-dry-run`
- Result before rollback: `0`
- Track: active Video playback / DOOM input prerequisite.
- Candidate reused: `A90 Linux init 0.10.65 (v2989-doominput-state)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img`
- Candidate SHA256: `30e37c64196e7ff2649291c1398c67e96efea9313b25c51dade39d1c62c9ccc2`
- Events: `event6,event8`
- Private run dir: `workspace/private/runs/input/v2991-doominput-dual-touch-live-20260620-181225`
- Live execution: `0`

## Preflight

- Preflight ok: `1`
- Candidate SHA256 ok: `1`
- Rollback v2321 SHA256 ok: `1`
- Fallback v2237 SHA256 ok: `1`
- Fallback v48 exists: `1`
- Flash helper exists: `1`
- Operator prerequisite: `operator finger movement during each bounded doominput touch window`

## Evidence

- Candidate version ok: `not-run`
- Candidate selftest fail=0: `not-run`
- Inputscan rc: `not-run` touch_candidates=`not-run`
- Candidate post-sample selftest fail=0: `not-run`

## Touch Candidates

- none captured in this run

## Per-Event Results

- none captured in this run

## Rollback Evidence

- Rollback attempted: `0`
- Rollback step ok: `0`
- Rollback health: version_ok=`0` selftest_fail0=`0`

## Interpretation

- V2991 stages one candidate boot that can sample both known MT-capable touch nodes instead of spending one flash/rollback per event.
- Pass requires at least one selected touch event to produce `doominput.state` touch evidence while candidate health remains clean.
- Dry-run mode does not flash; live mode still requires deliberate operator finger movement during each bounded sample window.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doominput_dual_touch_live_handoff_v2991.py tests/test_native_doominput_dual_touch_live_handoff_v2991.py`: PASS.
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doominput_dual_touch_live_handoff_v2991`: PASS (`6` tests).
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_dual_touch_live_handoff_v2991.py --events event6,event8 --count 32 --timeout-ms 45000`: PASS, dry-run preflight ok `1`, no flash.
- `git diff --check`: PASS.

## Safety

- Live mode flashes only the boot partition through `native_init_flash.py`; rollback target remains `v2321`.
- The validation path only reads `/sys/class/input` capability files and `/dev/input/event*` events.
- No input injection, `EVIOCGRAB`, keymap change, sysfs write, Wi-Fi, audio route/playback, video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Raw command output stays private under `workspace/private/runs/`; this report includes metadata only.
