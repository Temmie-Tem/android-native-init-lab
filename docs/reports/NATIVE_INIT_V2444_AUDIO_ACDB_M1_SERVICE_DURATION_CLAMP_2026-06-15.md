# NATIVE_INIT_V2444_AUDIO_ACDB_M1_SERVICE_DURATION_CLAMP_2026-06-15

## Summary

V2444 is a host-only fix for the V2443 helper startup wall. V2443 proved the M1 service
starts and finds target audio pids, but both helper processes printed usage and exited
because the generated `service.sh` passed `--duration-sec 180` while the V2423 helper
accepts only `1..120`.

V2444 fixes the shared M1 Magisk module template by clamping each helper invocation's
`--duration-sec` argument to the helper-supported maximum. It also adds a new V2444 runner
identity on top of the V2442 live wiring so the next live run has a distinct run/build tag.

No device action was performed in V2444.

## Changes

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_planner_v2429.py`
  - Adds `HELPER_MAX_DURATION_SEC = 120`.
  - Emits `HELPER_MAX_DURATION_SEC="120"` into generated `service.sh`.
  - Computes `helper_duration="$remaining"` per target pid.
  - Clamps `helper_duration` to `$HELPER_MAX_DURATION_SEC` before invoking the helper.
  - Passes `--duration-sec "$helper_duration"` instead of `--duration-sec "$remaining"`.
  - Logs `helper_duration` in `A90_M1_HELPER_START` so future private artifacts can confirm
    the bounded value.
- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py`
  - New V2444 runner identity, preserving V2442 live ordering and safety boundaries.
- `tests/test_native_audio_acdb_m1_magisk_module_planner_v2429.py`
  - Asserts the generated service has the helper max-duration constant and clamp.
  - Asserts the service no longer passes `$remaining` directly to `--duration-sec`.
- `tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py`
  - New runner tests copied from V2442 with V2444 identity and ordering regression.

## Safety Boundary

Unchanged:

- Android-good measurement only.
- Temporary Magisk `service.sh` module only.
- No native-init Magisk runtime dependency.
- No native speaker/mixer/PCM writes.
- No native `/dev/msm_audio_cal` ioctl.
- No native ACDB replay.
- Exact cleanup remains before checked V2321 rollback in live runs.

## Host Validation

Focused validation:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_planner_v2429.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py \
  tests/test_native_audio_acdb_m1_magisk_module_planner_v2429.py \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py

PYTHONPATH=tests python3 -m unittest \
  tests/test_native_audio_acdb_m1_magisk_module_planner_v2429.py \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2444.py
```

Focused result: `12` tests passed.

Materialized dry-run summary:

```json
{
  "run_id": "V2444",
  "decision": "v2444-acdb-m1-magisk-module-retry-live-dry-run",
  "ok": true,
  "future_live_ready": true,
  "command_safety_ok": true,
  "has_helper_max_duration": true,
  "uses_helper_duration": true,
  "uses_remaining_duration": false
}
```

Full validation:

```text
PYTHONPATH=tests python3 -m unittest discover -s tests
git diff --check
```

Full unittest discovery: `1214` tests passed. `git diff --check` passed.

## Next Unit

V2445 should be an exact-gated live rerun using the V2444 runner. Expected success condition
for the previously blocked edge is not yet payload capture; first prove the helper emits a
JSONL `start` event and `threadset-pass` / `tracee-add` telemetry instead of usage-only logs.
If helper starts and attaches but still sees zero `msm_audio_cal` ioctl entries while logcat
shows the ACDB edge, classify the next miss at the ptrace/filter level before considering
another Magisk timing escalation.
