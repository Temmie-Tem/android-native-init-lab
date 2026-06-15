# NATIVE_INIT_V2455_AUDIO_ACDB_M1_POST_MODULE_SETTLE_HARDENING_2026-06-15

## Summary

V2455 is a host-only hardening unit for the V2451 AUD-5L hybrid M1 late-observer
runner. It addresses the V2454 live failure where Android ADB returned after the
post-module reboot, but the fixed 30 second boot-complete recheck stayed empty
and hard-failed before the late observer, playback, or artifact collection.

## Change

- Added a V2451-local post-module settle wrapper.
- Kept the long `adb wait-for-device` reacquire after the temporary Magisk module
  reboot.
- Replaced the V2450 hard boot-complete recheck with a V2455 soft telemetry gate:
  it waits up to 180 seconds by default and records `A90_POST_MODULE_BOOT_COMPLETE_*`
  markers, but does not stop the run by itself.
- Kept Magisk `uid=0` root as the hard gate before late observer startup and
  `AudioTrack` playback.
- Exposed the new policy in dry-run output and tests:
  `boot_complete_soft_gate=true`, `root_check_hard_gate=true`.

## Magisk Direction

Magisk remains the same pattern that worked for Wi-Fi: an Android-good,
rollbackable measurement capsule. It is used to observe and stage the stock
Android audio path while native-init facts are still missing. It is not a
native-init runtime dependency and does not change the final native audio goal.

## Safety

- Host-only change; no device action, flash, playback, native calibration ioctl,
  mixer write, or speaker write was performed.
- The exact AUD-5L live approval phrase is unchanged.
- Cleanup and checked V2321 rollback paths are unchanged.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
- `PYTHONPATH=tests python3 -m unittest tests/test_native_audio_acdb_m1_hybrid_late_observer_live_handoff_v2451.py`
  - `Ran 8 tests`
  - `OK`
- Materialized dry-run:
  - `ok=true`
  - `future_live_ready=true`
  - `command_safety_ok=true`
  - `stage_wait_count=10`
  - `boot_complete_soft_gate=true`
  - `boot_complete_timeout_sec=180.0`
  - `root_check_hard_gate=true`
- `PYTHONPATH=tests python3 -m unittest discover -s tests`
  - `Ran 1242 tests`
  - `OK`
- `git diff --check`

## Next

Fresh exact-gated AUD-5L live rerun as V2456. The expected discriminator is
whether the post-module root gate becomes ready and the late observer captures
`/dev/msm_audio_cal` payload entries around Android `AudioTrack` speaker
playback.
