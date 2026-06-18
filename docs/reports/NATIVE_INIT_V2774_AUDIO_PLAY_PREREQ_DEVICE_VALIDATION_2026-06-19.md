# Native Init V2774 Audio Play Prerequisite Device Validation

## Summary

- Cycle: `V2774`
- Track: audio command play prerequisite device validation.
- Decision: `v2774-audio-play-prereq-device-pass`
- Result directory: `workspace/private/runs/audio/v2774-audio-play-prereq-device-validation-20260619-033108`
- Candidate image SHA256: `279989bda6c38cfceef61dc8611f90bc600a4e501e669d2278f62c2f639fd1b4`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2773 adds explicit PCM devnode prerequisite reporting before native ALSA open.
- This run records whether `audio play --execute` reports `/dev/snd/pcmC0D0p` missing and refuses before ALSA open on a baseline where `/dev/snd` is not materialized.
- Expected pass: `bounded-pcm-playback.native_implemented=1`, `audio.play.refused=missing-pcm-node`, and `audio.play.execute.alsa_open_attempted=0`.
- This keeps the play primitive API explicit: playback requires the speaker preparation stages (`/dev/snd`, app-type, SET replay, route) first.

## Command Summary

- `audio-status`: ok=True rc=0 dry_run_ok=False old_refusal=False execute_supported=False prereq_missing=False missing_pcm_refusal=False open_attempt=False open_suppressed=False bounded_native=False hw_params=False prepare=False write_attempt=False done=False
- `audio-profiles`: ok=True rc=0 dry_run_ok=False old_refusal=False execute_supported=False prereq_missing=False missing_pcm_refusal=False open_attempt=False open_suppressed=False bounded_native=False hw_params=False prepare=False write_attempt=False done=False
- `audio-profile`: ok=True rc=0 dry_run_ok=False old_refusal=False execute_supported=False prereq_missing=False missing_pcm_refusal=False open_attempt=False open_suppressed=False bounded_native=False hw_params=False prepare=False write_attempt=False done=False
- `audio-stages`: ok=True rc=0 dry_run_ok=False old_refusal=False execute_supported=False prereq_missing=False missing_pcm_refusal=False open_attempt=False open_suppressed=False bounded_native=True hw_params=False prepare=False write_attempt=False done=False
- `audio-play-dry-run`: ok=True rc=0 dry_run_ok=True old_refusal=False execute_supported=True prereq_missing=True missing_pcm_refusal=False open_attempt=False open_suppressed=False bounded_native=False hw_params=False prepare=False write_attempt=False done=False
- `audio-play-execute-native-pcm`: ok=True rc=-2 dry_run_ok=False old_refusal=False execute_supported=True prereq_missing=True missing_pcm_refusal=True open_attempt=False open_suppressed=True bounded_native=False hw_params=False prepare=False write_attempt=False done=False

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- No credentials are used.
- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.
