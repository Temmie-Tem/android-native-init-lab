# NATIVE_INIT_V2453_AUDIO_ACDB_M1_STAGE_ADB_WAIT_HARDENING_2026-06-15

## Summary

V2453 hardens the V2451 hybrid M1 late-observer runner after V2452 failed at
`stage-2` with `adb: no devices/emulators found`.

V2452 proved Android ADB can transiently disappear between staged shell commands after
the initial Android boot/root settle. V2451 only inserted `adb wait-for-device` before
`adb push` and `adb install`, so shell stages were still exposed to that transient gap.

## Change

Updated:

- `workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`

The runner now:

- waits for ADB before every staged `adb shell`;
- continues waiting before every staged `adb push`;
- continues waiting before staged `adb install`;
- exposes the expanded wait plan in dry-run output.

The resulting materialized dry-run reports `10` staged wait entries:

- `shell`
- `shell`
- `shell`
- `shell`
- `push`
- `push`
- `push`
- `push`
- `install`
- `shell`

This keeps all V2451 safety boundaries unchanged. It does not alter the module payload,
late observer helper, cleanup policy, Android boot image, rollback image, or exact live
approval phrase.

## Validation

Host-only validation performed:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py` (`7` tests)
- `python3 workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py --dry-run --materialize-module-template`

Dry-run result:

- `ok=true`
- `future_live_ready=true`
- `command_safety_ok=true`
- `stage_wait_count=10`

No device action was run in this unit.

## Next Unit

Rerun AUD-5L as a fresh live iteration. The expected discriminator remains:

- payload captured from `/dev/msm_audio_cal`, or
- no payload with late-observer terminal evidence identifying whether this is still fd-miss,
  no-ioctl, or no-target-pid behavior.
