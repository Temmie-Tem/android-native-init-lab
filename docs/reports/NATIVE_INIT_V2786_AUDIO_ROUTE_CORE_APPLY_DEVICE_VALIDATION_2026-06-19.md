# Native Init V2786 Audio Route Core Apply Device Validation

## Summary

- Cycle: `V2786`
- Track: audio route core apply/reset device validation.
- Decision: `v2786-audio-route-core-apply-device-pass`
- Result directory: `workspace/private/runs/audio/v2786-audio-route-core-apply-device-validation-20260619-054300`
- Candidate image SHA256: `8f029c7e8480cf334640704a3e1bc68570a6ee427acb9a4b790277005e5a7e06`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2786 flashes the V2786 boolean-core route test image and validates the first bounded write path exposed by the modularized route API.
- The live window keeps the serial path minimal: settle menu, activate ADSP, materialize `/dev/snd`, dry-run the core route, apply only `--layer core`, reset only `--layer core`, then roll back to V2321.
- V2786 uses a readiness-based runner path: one-shot ADSP and /dev/snd commands are sent through the slow-input a90ctl path, while pass/fail depends on the resulting sound-control and /dev/snd readiness plus route apply/reset markers.
- Expected pass: `audio.adsp_boot_once.write=accepted`, `audio.snd_materialize.version=1`, `audio.route.write_done count=6 layer=core mode=apply`, `audio.route.write_done count=5 layer=core mode=reset`, no route refusal/write failure, and final rollback `selftest fail=0`.

## Command Summary

- `audio-snd-status-before-adsp`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-adsp-boot-once`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-snd-status-before-materialize`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-snd-materialize-once`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=1 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-snd-status-after-materialize`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-route-dry-run-core`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-route-apply-core`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=1 core_reset=0 route_refused=False route_failed=False prereq_error=False
- `audio-route-reset-core`: ok=True rc=0 audio=True prereq_version=False stage_order=False snd_materialize=0 core_apply=0 core_reset=1 route_refused=False route_failed=False prereq_error=False

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Audio writes are limited to the known-safe core route apply/reset controls.
- No feedback/endpoint/blocked smart-amp route layer is written.
- No ACDB SET, PCM open, PCM write, or playback execute is performed by this validation.
- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.
