# Native Init V2793 Audio Play Worker Live Handoff

## Summary

- Cycle: `V2793`
- Track: audio core closure gate.
- Decision: `v2793-audio-play-worker-live-worker-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2793-audio-play-worker-20260619-075835`
- Candidate tag: `v2793-audio-play-worker`
- Candidate image SHA256: `c2db9019620556c42e1fdf53ca86b03ebf3ad27ce5c3c5a138504b3b95d7b402`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `0`
- Worker status done/attempts: `1` / `2`
- Worker status stdout: `workspace/private/runs/audio/v2793-audio-play-worker-20260619-075835/30_candidate-audio-play-status-02.txt`
- Worker log stdout: `workspace/private/runs/audio/v2793-audio-play-worker-20260619-075835/31_candidate-audio-play-worker-log.txt`
- Worker started/done: `1` / `0`
- Listen window begin/end: `0 / 0`
- Integrated done: `0`
- SET-cal hold/all-set/dealloc: `0 / 0 / 0`
- Route apply/reset OK: `0 / 0`
- PCM write/done: `0 / 0`
- Safety amplitude/duration cap: `1 / 1`

## Root Cause Note

- The initial live runner tried `run /bin/cat /cache/a90-audio-play/worker.log`, but this image has no `/bin/cat`; the log retrieval command failed with `execve(/bin/cat): No such file or directory`.
- A post-rollback manual recovery used `/bin/busybox cat` against the persisted `/cache/a90-audio-play/worker.log`.
- The worker architecture itself worked: parent returned immediately, child started, ADSP boot reached `audio.play.integrated.wait.sound_control.ready=1 elapsed_ms=1000`, `/dev/snd` materialization succeeded, and App Type Config write succeeded.
- The worker stopped at SET-cal verify with `audio.setcal.verify.path_allowed=0`, `audio.setcal.verify.error=manifest-path-not-allowed`, and `audio.play.integrated.done=0 rc=-22`.
- Next unit: allow the legacy replay manifest prefix for manifest files as already allowed for payload files, and switch the live runner log retrieval to `/bin/busybox cat`.

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
