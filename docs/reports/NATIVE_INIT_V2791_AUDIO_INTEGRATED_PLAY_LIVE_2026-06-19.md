# Native Init V2791 Integrated Audio Playback Live Handoff

## Summary

- Cycle: `V2791`
- Track: audio core closure gate.
- Decision: `v2791-audio-integrated-play-live-blocked`
- Result directory: `workspace/private/runs/audio/v2791-audio-integrated-play-20260619-070955`
- Candidate tag: `v2791-audio-integrated-play`
- Candidate image SHA256: `e08c0eda55d8e12937a5413c4c8f46205f41ae6e0523a69202e421d09c809d90`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest --execute`
- Play rc: `None`
- Listen window begin/end: `0 / 0`
- Integrated done: `0`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `0 / 0`

## Runtime Artifacts

- Deploy plan: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`
- Native manifest remote path: `/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest`
- Native manifest SHA256: `9be68f78bf8f4d8798e45b7b73e4a3328e6ce31ef476272700dfe3bfe7c1d518`
- No runtime artifact installs recorded.

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache`.
- No forbidden partitions are touched.
- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.
