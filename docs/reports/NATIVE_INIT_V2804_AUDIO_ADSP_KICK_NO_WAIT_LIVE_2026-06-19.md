# Native Init V2804 Audio ADSP Kick No-Wait Live Handoff

## Summary

- Cycle: `V2804`
- Track: audio core closure gate.
- Decision: `v2804-audio-adsp-kick-no-wait-worker-failed-before-rollback`
- Result directory: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429`
- Candidate tag: `v2804-audio-adsp-kick-no-wait`
- Candidate image SHA256: `cd2822e6abeaf81320f16d081a5569ee27626954205ab3b4b4b38ad905e45d09`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Playback Evidence

- Native command: `audio play internal-speaker-safe --mode listen --duration-ms 8000 --amplitude-milli 150 --manifest /cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest --execute`
- Play start rc: `0`
- Worker status done/attempts: `1` / `30`
- Worker status stdout: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/60_candidate-audio-play-status-30.txt`
- Worker log stdout: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/61_candidate-audio-adsp-kick-no-wait-log.txt`
- Worker started/done: `1` / `0`
- Listen window begin/end: `0 / 0`
- Foreground ADSP kick seen/ok/no-wait/failed: `1 / 1 / 1 / 0`
- Worker ADSP prebooted / second boot skipped: `1 / 1`
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

## Diagnostic Captures

- ADSP status before play: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/06_candidate-audio-adsp-status-before-play.txt`
- SND status before play: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/07_candidate-audio-snd-status-before-play.txt`
- ADSP status after play: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/62_candidate-audio-adsp-status-after-play.txt`
- SND status after play: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/63_candidate-audio-snd-status-after-play.txt`
- Dmesg audio tail: `workspace/private/runs/audio/v2804-audio-adsp-kick-no-wait-20260619-100429/64_candidate-dmesg-audio-tail.txt`

## Live Classification

- The no-wait foreground ADSP kick behaved as intended: the command accepted `audio.adsp_boot_once`, did not wait in PID1, returned `rc=0`, and spawned the worker in about 30 ms.
- The worker correctly consumed the foreground-kick contract: `audio.play.integrated.adsp_prebooted=1`, `audio.play.integrated.adsp.boot_allowed=0`, and `audio.play.integrated.adsp.boot_skipped=1`.
- The failure moved to the ASoC publication gate. After the worker waited 70.25 s, `audio.play.integrated.wait.sound_control.ready=0`, `/proc/asound/cards` still reported `--- no soundcards ---`, and no `card*` or `control*` nodes were present.
- The ADSP itself was not dead: post-play status showed ADSP-like rpmsg channels, `apr_audio_svc`, and FastRPC class entries. The missing state is the `sm8150-tavil-snd-card`/sound-control publication required before ION, `/dev/msm_audio_cal`, route, SET-cal, or PCM can start.
- This is a different result from V2802, where direct `audio adsp-boot-once` published `sm8150-tavil-snd-card` quickly. The next discriminator should reproduce the V2802-style direct ADSP/card publication before runtime ACDB artifact staging, then run the already-up-card `audio play --execute` path.

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
