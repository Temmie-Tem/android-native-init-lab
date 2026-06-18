# NATIVE_INIT V2746 Audio Listen Test Hard-Timeout Observation Fix

## Purpose

Prevent the listen-test live runner from hanging before playback. Two live attempts reached V2334 `candidate-version` and then stalled before any audio step or `A90_LISTEN_WINDOW_*` marker. The device remained healthy, but the in-process serial observation path held the serial transaction lock and blocked forward progress.

## Change

- Added `run_a90ctl_hard_observation()` to the V2639/V274x runner.
- Observation commands now call `a90ctl.py` as a subprocess with `--hide-on-busy`, `--input-mode slow`, and a subprocess-level hard timeout.
- Replaced the live runner's candidate/status/audio-status/rollback-version observation calls with the hard-timeout wrapper.
- Replaced the V2639-local selftest wrapper with the same hard-timeout observation path.

## Scope

This applies only to read-only observation commands in `native_audio_acdb_setcal_replay_live_handoff_v2639.py`. It does not change ACDB SET replay, route controls, PCM playback, rollback image selection, or audio safety parameters.

## Recovery From Failed Attempt

The V2746 pre-fix attempt did not reach playback. It was stopped while still before audio materialization and recovered to V2321 through the checked flash helper from TWRP recovery.

- V2321 boot readback SHA matched.
- Post-rollback version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- Post-rollback status included `selftest: ... fail=0`.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `git diff --check`

## Next

Re-run the bounded listen test. A successful run should now progress past candidate health, print the host countdown marker, execute the 8 s remote listen window, and roll back to V2321.
