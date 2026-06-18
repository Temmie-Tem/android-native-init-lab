# Native Init V2784 Audio Route API Device Validation

## Summary

- Cycle: `V2784`
- Track: audio route API module device validation.
- Decision: `v2784-audio-route-api-device-pass`
- Result directory: `workspace/private/runs/audio/v2784-audio-route-api-device-validation-20260619-050114`
- Candidate image SHA256: `5ccea5238d5719ed43a015db2502a616be786a4245c502fb530cf4aed4b1eba2`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2783 splits pure route and speaker-map query helpers into `a90_audio_route.{h,c}` while preserving the read-only native-init API surface.
- This run flashes the V2783 test image, checks route-API-backed read-only audio commands on device, confirms speaker-map and route dry-run output survive the module split, then rolls back to V2321.
- V2784 uses the V2781 hardened runner path: selftest validation accepts the structured protocol envelope when the human text stream is desynchronized, and rollback can fall back to recovery-mode flashing if native-to-recovery handoff times out after the device reaches recovery.
- Expected pass: `audio.prereq.read_only=1`, `audio.speaker_map.version=1`, `audio.route.version=1`, route dry-run markers, no `audio.prereq.error`, and final rollback `selftest fail=0`.

## Command Summary

- `audio-status`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=0 prereq_error=False
- `audio-profiles`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=0 prereq_error=False
- `audio-profile`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=0 prereq_error=False
- `audio-speaker-map`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=1 route=0 prereq_error=False
- `audio-stages`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=0 prereq_error=False
- `audio-prereq`: ok=True rc=0 audio=True prereq_version=True read_only=True stage_order=True commands=1 snd_ready=True play_dry_run_ok=False speaker_map=0 route=0 prereq_error=False
- `audio-route-dry-run-all`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=1 prereq_error=False
- `audio-route-dry-run-core`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=False speaker_map=0 route=1 prereq_error=False
- `audio-play-dry-run`: ok=True rc=0 audio=True prereq_version=False read_only=False stage_order=False commands=0 snd_ready=False play_dry_run_ok=True speaker_map=0 route=0 prereq_error=False

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- No audio route apply, ACDB SET, PCM open, mixer write, or playback execute is performed by this validation.
- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.
