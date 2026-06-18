# Native Init V2778 Audio Profile Module Device Validation

## Summary

- Cycle: `V2778`
- Track: audio profile module device validation.
- Decision: `v2778-audio-profile-module-device-pass`
- Result directory: `workspace/private/runs/audio/v2778-audio-profile-module-device-validation-20260619-041157`
- Candidate image SHA256: `f4c3efc553f79d16f28d5de09edd971bff95dd192718ac8083cdf8b6c7fa7f95`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2777 splits the canonical internal-speaker profile and route data into `a90_audio_profile.{h,c}` while preserving the read-only native-init API surface.
- This run flashes the V2777 test image, checks the profile-backed read-only audio commands on device, confirms prereq does not claim runtime state is verified, then rolls back to V2321.
- Expected pass: `audio.prereq.read_only=1`, `write_attempted=0`, `playback_attempted=0`, all stage commands present, no `audio.prereq.error`, and final rollback `selftest fail=0`.

## Command Summary

- `audio-status`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False dry_run_ok=False prereq_error=False
- `audio-profiles`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False dry_run_ok=False prereq_error=False
- `audio-profile`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False dry_run_ok=False prereq_error=False
- `audio-stages`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False dry_run_ok=False prereq_error=False
- `audio-prereq`: ok=True rc=0 audio=True prereq_version=True read_only=True stage_order=True commands=1 snd_ready=True dry_run_ok=False prereq_error=False
- `audio-play-dry-run`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False dry_run_ok=True prereq_error=False

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- No audio route apply, ACDB SET, PCM open, mixer write, or playback execute is performed by this validation.
- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.
