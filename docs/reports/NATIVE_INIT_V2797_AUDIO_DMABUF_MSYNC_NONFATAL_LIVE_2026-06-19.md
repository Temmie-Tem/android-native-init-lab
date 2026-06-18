# Native Init V2797 Audio DMABUF Msync Nonfatal Live Handoff

## Summary

- Cycle: `V2797`
- Track: audio core closure gate.
- Decision: `v2797-audio-dmabuf-msync-nonfatal-live-worker-failed-before-rollback`
- Result: PARTIAL PROGRESS — V2796's dmabuf `msync(EINVAL)` blocker is cleared as non-fatal; all 11 SET-cal entries prepared, then `/dev/msm_audio_cal` open failed with `errno=2`.
- Result directory: `workspace/private/runs/audio/v2797-audio-dmabuf-msync-nonfatal-20260619-084341`
- Candidate tag: `v2797-audio-dmabuf-msync-nonfatal`
- Candidate image SHA256: `4d3a5b9efa1c3734b304d45d656a5fc48322439a647ef1da857da6a6bb849d1c`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `0`
- Worker status done/attempts: `1` / `2`
- Worker status stdout: `workspace/private/runs/audio/v2797-audio-dmabuf-msync-nonfatal-20260619-084341/30_candidate-audio-play-status-02.txt`
- Worker log stdout: `workspace/private/runs/audio/v2797-audio-dmabuf-msync-nonfatal-20260619-084341/31_candidate-audio-dmabuf-msync-nonfatal-log.txt`
- Worker started/done: `1` / `0`
- Listen window begin/end: `0 / 0`
- Integrated done: `0`
- ION materialize seen/ok/alloc: `1 / 1 / 1`
- DMABUF msync nonfatal / SET entries prepared / msm_audio_cal missing: `1 / 1 / 1`
- New blocker: `audio.setcal.execute.open.msm_audio_cal.open_ok=0 errno=2` after `audio.setcal.execute.prepared_count=11`; no `/dev/msm_audio_cal` SET ioctl, route apply, or PCM write was attempted.
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

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache`.
- No forbidden partitions are touched.
- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.

## Interpretation

- V2796's blocker is resolved: mapped dmabuf `msync()` still returns `EINVAL`, but V2797 records `msync_nonfatal=1`, copies payloads, and continues.
- The executor prepared all 11 manifest entries, including the four dmabuf payload entries, proving the source-side SET replay materialization is now complete.
- The next narrow blocker is the runtime `/dev/msm_audio_cal` devnode: it was absent when the executor tried to open it, so zero calibration ioctls were attempted.
- Rollback to `v2321` completed and `selftest fail=0`.
