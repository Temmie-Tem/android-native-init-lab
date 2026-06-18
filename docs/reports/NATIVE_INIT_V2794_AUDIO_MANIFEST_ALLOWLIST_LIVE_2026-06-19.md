# Native Init V2794 Audio Manifest Allowlist Live Handoff

## Summary

- Cycle: `V2794`
- Track: audio core closure gate.
- Decision: `v2794-audio-manifest-allowlist-live-worker-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2794-audio-manifest-allowlist-20260619-080819`
- Candidate tag: `v2794-audio-manifest-allowlist`
- Candidate image SHA256: `8f10de026dfba91f880e144684002da8681a438c6faa10f1e34162e9864b6a94`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `0`
- Worker status done/attempts: `0` / `100`
- Worker status stdout: `workspace/private/runs/audio/v2794-audio-manifest-allowlist-20260619-080819/128_candidate-audio-play-status-100.txt`
- Worker log stdout: `workspace/private/runs/audio/v2794-audio-manifest-allowlist-20260619-080819/129_candidate-audio-manifest-allowlist-log.txt`
- Worker started/done: `1` / `0`
- Listen window begin/end: `0 / 0`
- Integrated done: `0`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `1 / 1`

## Runtime Artifacts

- Deploy plan: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`
- Native manifest remote path: `/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest`
- Native manifest SHA256: `9be68f78bf8f4d8798e45b7b73e4a3328e6ce31ef476272700dfe3bfe7c1d518`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/00-set-arg-cal39-core-custom-topologies.bin`
- `payload` `/cache/a90-acdb-setcal-replay-v2725/00-payload-cal39-core-custom-topologies.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/01-set-arg-cal20-realhal-01.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/02-set-arg-cal20-realhal-02.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/03-set-arg-cal13.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/04-set-arg-cal09.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/05-set-arg-cal11.bin`
- `payload` `/cache/a90-acdb-setcal-replay-v2725/05-payload-cal11.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/06-set-arg-cal12.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/07-set-arg-cal15.bin`
- `payload` `/cache/a90-acdb-setcal-replay-v2725/07-payload-cal15.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/08-set-arg-cal23.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/09-set-arg-cal16.bin`
- `payload` `/cache/a90-acdb-setcal-replay-v2725/09-payload-cal16.bin`
- `set_arg` `/cache/a90-acdb-setcal-replay-v2725/10-set-arg-cal21.bin`
- `native_manifest` `/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest`

## Failure Localization

- V2794 fixed the immediate V2793 blocker: the worker log shows `audio.setcal.verify.path_allowed=1` for `/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest`.
- The worker verified the cal39 arg and payload metadata path/size/SHA, then stopped before `audio.setcal.execute.hold_active=1`, route apply, listen window, or PCM write markers.
- `audio play-status` stayed `done=0` through 100 polls; the run therefore classified as worker-failed, not sound-producing.
- Rollback to `v2321` completed and post-rollback `selftest verbose` reported `fail=0`.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache`.
- No forbidden partitions are touched.
- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.
