# Native Init V2798 Audio MSM Audio Cal Devnode Live Handoff

## Summary

- Cycle: `V2798`
- Track: audio core closure gate.
- Decision: `v2798-audio-msm-audio-cal-devnode-live-worker-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2798-audio-msm-audio-cal-devnode-20260619-085346`
- Candidate tag: `v2798-audio-msm-audio-cal-devnode`
- Candidate image SHA256: `2e0e0768ecbaee3c2ffd3074ec600c7780ba265a7beea983900a33a76542060c`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `0`
- Worker status done/attempts: `1` / `2`
- Worker status stdout: `workspace/private/runs/audio/v2798-audio-msm-audio-cal-devnode-20260619-085346/30_candidate-audio-play-status-02.txt`
- Worker log stdout: `workspace/private/runs/audio/v2798-audio-msm-audio-cal-devnode-20260619-085346/31_candidate-audio-msm-audio-cal-devnode-log.txt`
- Worker started/done: `1` / `0`
- Listen window begin/end: `0 / 0`
- Integrated done: `0`
- ION materialize seen/ok/alloc: `1 / 1 / 1`
- MSM audio cal materialize seen/ok/open/missing: `1 / 1 / 1 / 0`
- DMABUF msync nonfatal / SET entries prepared: `1 / 1`
- SET-cal first ioctl EFAULT / allocate EFAULT: `1 / 1`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `1 / 1`

## Next Blocker

- V2798 passed the intended devnode gate: `/sys/class/misc/msm_audio_cal/dev` reported `10:54`, `/dev/msm_audio_cal` was created, and `open_ok=1`.
- The new blocker is the first `AUDIO_ALLOCATE_CALIBRATION` ioctl: `audio.setcal.execute.ioctl.0.rc=-1 errno=14` and `audio.setcal.execute.allocate_failed.index=0 errno=14`.
- This localizes V2799 to the SET-cal ioctl argument/mem-handle ABI, not device-node reachability.

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
