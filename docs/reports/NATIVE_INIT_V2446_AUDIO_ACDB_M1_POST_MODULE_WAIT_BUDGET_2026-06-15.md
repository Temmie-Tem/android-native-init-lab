# NATIVE_INIT_V2446_AUDIO_ACDB_M1_POST_MODULE_WAIT_BUDGET_2026-06-15

## Summary

V2446 is a host-only fix for the V2445 post-module ADB timeout. V2445 showed that Android
ADB returned about `206.359s` after the Magisk module activation reboot, while the runner's
post-module `adb wait-for-device` step used the generic `120s` ADB command timeout.

V2446 creates a new runner identity on top of V2444 and separates the post-module
`wait-for-device` timeout from the generic ADB timeout. The new default is `300s`, which is
above the observed V2445 return time while preserving the same M1 Android-good measurement
boundary.

No device action was performed in V2446.

## Changes

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2446.py`
  - New V2446 runner identity with build tag `v2446-audio-acdb-m1-post-module-wait`.
  - Adds `DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC = 300.0`.
  - Adds CLI option `--post-module-adb-wait-timeout`.
  - Uses that dedicated timeout for post-module `adb wait-for-device` calls.
  - Records `adb_wait_timeout_sec` and the observed V2445 return time (`206.359s`) in the
    dry-run plan.
  - Leaves staging, incoming SHA validation, V2444 `service.sh` duration clamp, cleanup,
    rollback, helper payload, and native-audio safety boundaries unchanged.
- `tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2446.py`
  - New focused V2446 runner test set.
  - Asserts the dry-run exposes the `300s` post-module ADB wait budget.
  - Asserts the budget is greater than both the old `120s` generic timeout and the observed
    V2445 `206.359s` ADB return.
  - Asserts post-module wait records use the dedicated timeout.

## Safety Boundary

Unchanged from V2444/V2445:

- Android-good measurement only.
- Temporary Magisk `service.sh` module only.
- No native-init Magisk runtime dependency.
- No native speaker/mixer/PCM writes.
- No native `/dev/msm_audio_cal` ioctl.
- No native ACDB replay.
- Exact cleanup remains before checked V2321 rollback in live runs.

## Validation

Focused validation:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2446.py \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2446.py

PYTHONPATH=tests python3 -m unittest \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2446.py
```

Focused result: `8` tests passed.

Materialized dry-run summary:

```json
{
  "run_id": "V2446",
  "build_tag": "v2446-audio-acdb-m1-post-module-wait",
  "decision": "v2446-acdb-m1-magisk-module-retry-live-dry-run",
  "future_live_ready": true,
  "command_safety_ok": true,
  "adb_wait_timeout_sec": 300.0,
  "observed_v2445_sec": 206.359
}
```

Full validation:

```text
PYTHONPATH=tests python3 -m unittest discover -s tests
git diff --check
```

Full unittest discovery: `1222` tests passed. `git diff --check` passed.

## Next Unit

V2447 should be an exact-gated live rerun using the V2446 runner. The first success
criterion remains helper JSONL startup/trace telemetry. If the longer wait reaches
logcat/playback/artifact collection but captures zero ioctl entries while Android logcat shows the
ACDB edge, classify the ptrace/filter/timing boundary from the helper JSONL and logs before any
native replay work.
