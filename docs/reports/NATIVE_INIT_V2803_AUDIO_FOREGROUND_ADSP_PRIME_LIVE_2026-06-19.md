# Native Init V2803 Audio Foreground ADSP Prime Live Handoff

## Summary

- Cycle: `V2803`
- Track: audio core closure gate.
- Decision: `v2803-audio-foreground-adsp-prime-start-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2803-audio-foreground-adsp-prime-20260619-095145`
- Candidate tag: `v2803-audio-foreground-adsp-prime`
- Candidate image SHA256: `03a126660a94fc37fe28ad7ab42ea4526e854f8c58663bb9408ac6118a0e6b97`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `-110`
- Worker status done/attempts: `0` / `None`
- Worker status stdout: `None`
- Worker log stdout: `None`
- Worker started/done: `0` / `0`
- Listen window begin/end: `0 / 0`
- Foreground ADSP prime seen/ok/failed: `1 / 0 / 1`
- Integrated done: `0`
- Sound-control ready/timeout: `0` / `1`
- ION materialize seen/ok/alloc: `0 / 0 / 0`
- MSM audio cal materialize seen/ok/open/missing: `0 / 0 / 0 / 0`
- DMABUF msync nonfatal / SET entries prepared: `0 / 0`
- SET-cal native allocate/set request seen: `0 / 0`
- SET-cal first ioctl EFAULT / allocate EFAULT: `0 / 0`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `1 / 1`

## Live Classification

- Foreground-prime code executed inside `audio play --execute`: `audio.play.execute.foreground_prime_adsp=1`.
- The ADSP boot write was accepted, but `sound_control` never appeared inside the in-command 70 s wait: `audio.play.integrated.wait.sound_control.ready=0 elapsed_ms=70250`.
- The command returned `-ETIMEDOUT` before spawning the async playback worker, so no SET-cal, route, PCM, or worker cleanup path was reached.
- Rollback to `v2321` completed with `selftest fail=0`.
- This is not a regression of the direct ADSP path proven by V2802; it exposes a narrower ordering/context gap: the same boot image can publish ASoC from standalone `audio adsp-boot-once`, but the in-command foreground-prime path still timed out. Next unit should capture full dmesg/ADSP/SND snapshots immediately after the in-command timeout before rollback.

## Diagnostic Captures

- ADSP status before play: `workspace/private/runs/audio/v2803-audio-foreground-adsp-prime-20260619-095145/06_candidate-audio-adsp-status-before-play.txt`
- SND status before play: `workspace/private/runs/audio/v2803-audio-foreground-adsp-prime-20260619-095145/07_candidate-audio-snd-status-before-play.txt`
- ADSP status after play: `None`
- SND status after play: `None`
- Dmesg audio tail: `None`

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
