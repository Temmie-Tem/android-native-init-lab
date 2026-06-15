# NATIVE_INIT_V2442_AUDIO_ACDB_M1_POST_MODULE_SETTLE_WIRING_FIX_2026-06-15

## Summary

V2442 is a host-only wiring fix for the V2441 live result. V2441 proved that V2440's
bounded post-module-root retry existed but was attached to the wrong reboot boundary:
`run_live()` called `run_post_module_reboot_settle()` immediately after the initial Android
flash, then still used the older single-shot `v2396.run_android_post_handoff_settle()`
after the actual Magisk `service.sh` activation reboot.

V2442 preserves the V2438/V2440 staging and safety model and changes only the live settle
ordering:

1. Initial Android flash handoff uses the established Android post-handoff settle.
2. Module files are staged and installed exactly as before.
3. Android reboots once for Magisk `service.sh` activation.
4. The bounded V2440 root retry now runs after that module-activation reboot.
5. Logcat/playback/artifact collection can only begin after the post-module retry observes
   `uid=0`.

No live device action was performed in V2442.

## Files

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py`
- `tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py`

## Safety Boundary

Unchanged from V2440/V2441:

- Android-good measurement only.
- Temporary Magisk `service.sh` module only.
- No native-init Magisk runtime dependency.
- No native speaker/mixer/PCM writes.
- No native `/dev/msm_audio_cal` ioctl.
- No native ACDB replay.
- Exact cleanup remains before checked V2321 rollback in live runs.

## Host Validation

Materialized dry-run summary:

```json
{
  "run_id": "V2442",
  "decision": "v2442-acdb-m1-magisk-module-retry-live-dry-run",
  "ok": true,
  "future_live_ready": true,
  "command_safety_ok": true,
  "post_module_retry": 8
}
```

Validation commands:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py \
  --materialize-module --dry-run

PYTHONPATH=tests python3 -m unittest \
  tests/test_native_audio_acdb_m1_magisk_module_retry_live_handoff_v2442.py

PYTHONPATH=tests python3 -m unittest discover -s tests

git diff --check
```

Results:

- Focused V2442 tests: `8` passed.
- Full unittest discovery: `1206` passed.
- `git diff --check`: passed.

## Regression Guard

The new ordering regression checks the relevant source order:

```text
flash-android
v2396.run_android_post_handoff_settle(...)
stage_commands(...)
android-reboot-for-magisk-service
run_post_module_reboot_settle(...)
logcat-clear-before-stimulus
```

This prevents the exact V2441 failure mode from returning: after the Magisk module
activation reboot, the next settle edge must be `android-post-module-reboot-root-check-*`,
not the old `android-post-handoff-settle-2` single-shot root check.

## Next Unit

V2443 should be the exact-gated live rerun using the V2442 runner. It should retain the
same M1 boundary and stop before any native replay design. If the run reaches artifacts,
analyze command order, decoded headers, private payload hashes, mem-handle policy, and
cleanup behavior before any native ACDB replay work.
