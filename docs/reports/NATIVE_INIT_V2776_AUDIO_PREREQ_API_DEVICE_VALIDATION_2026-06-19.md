# Native Init V2776 Audio Prerequisite API Device Validation

## Summary

- Cycle: `V2776`
- Track: audio prerequisite API device validation.
- Decision: `v2776-audio-prereq-api-device-pass`
- Result directory: `workspace/private/runs/audio/v2776-audio-prereq-api-device-validation-20260619-035224`
- Candidate image SHA256: `7a4391737eb28fc5d3b99a75ccbc7bc5b729f056c4e4eb40fb8dba8992fa3c02`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2775 adds `audio prereq [profile]` as a read-only native-init API surface for the speaker preparation contract.
- This run flashes the V2775 test image, checks the prereq command on device, confirms it does not claim runtime state is verified, then rolls back to V2321.
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
