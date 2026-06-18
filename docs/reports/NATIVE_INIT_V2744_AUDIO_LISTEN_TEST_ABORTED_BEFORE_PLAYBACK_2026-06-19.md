# NATIVE_INIT V2744 Audio Listen Test Aborted Before Playback

## Decision

`v2744-listen-test-aborted-before-playback-code-bug`

## What Happened

The first human-audible listen-test live run started from V2321 and flashed V2334 successfully, but it never reached the audio playback window. No `A90_LISTEN_WINDOW_BEGIN` marker was emitted and no PCM probe ran.

The run failed while generating the local 8 s WAV metadata:

```text
AttributeError: module 'native_audio_speaker_pilot_live_handoff_v2379' has no attribute 'sha256_file'
```

The V2743 support code called `speaker.sha256_file(...)`; the actual helper is `speaker.recipe.sha256_file(...)`.

## Evidence

- Run dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260619-000436`
- Last completed live step before the bug: candidate `version` on V2334.
- No listen markers were present in the run artifacts.
- Manual operator observation of silence is consistent with the code path: playback had not started.

## Recovery

The interrupted run was recovered by flashing the V2321 rollback image through the checked flash helper from TWRP recovery.

- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Flash helper readback SHA matched.
- Post-rollback version: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Post-rollback selftest: `fail=0`

## Fix

- Replace the bad hash call with `speaker.recipe.sha256_file(...)`.
- Add a unit test that actually generates the V2743 8 s WAV and validates the recorded SHA.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90ctl.py version`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest verbose`
- `git diff --check`

## Next

Re-run the bounded human-audible listen test as the next live iteration. The prior silence does not classify audio output because the playback window never started.
