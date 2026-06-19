# Native Init V2806 Audio Deploy-First ADSP Probe Live Handoff

## Summary

- Cycle: `V2806`
- Track: audio core closure gate discriminator.
- Decision: `v2806-deploy-first-direct-adsp-no-card-before-rollback`
- Result directory: `workspace/private/runs/audio/v2806-audio-deploy-first-adsp-probe-20260619-103842`
- Candidate tag/version: `v2804-audio-adsp-kick-no-wait` / `0.9.314`
- Candidate image SHA256: `cd2822e6abeaf81320f16d081a5569ee27626954205ab3b4b4b38ad905e45d09`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Discriminator Evidence

- Runtime artifact staging happened before direct ADSP boot: `1`
- Pre-deploy card/control: `0 / 0`
- After-deploy before-ADSP card/control: `0 / 0`
- Direct ADSP command: `audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT`
- Direct ADSP rc/accepted: `0` / `1`
- Direct ADSP stdout: `workspace/private/runs/audio/v2806-audio-deploy-first-adsp-probe-20260619-103842/32_candidate-audio-direct-adsp-boot-once-after-deploy.txt`
- Card ready after deploy+ADSP: `0` after `35` polls
- Card poll last summary: `{"dev_snd_line": "audio.dev_snd.count=0 control_like=0 pcm_like=0", "has_adsp_rpmsg": true, "has_sound_card": false, "has_sound_control": false, "no_soundcards": true, "proc_asound_cards_line": "audio.proc_asound_cards=--- no soundcards ---", "rpmsg_line": "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0", "sound_class_line": "audio.sound_class.count=1 card_like=0 control_like=0"}`
- Dmesg audio tail: `workspace/private/runs/audio/v2806-audio-deploy-first-adsp-probe-20260619-103842/103_candidate-dmesg-audio-tail.txt`

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
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache` before direct ADSP boot.
- No forbidden partitions are touched.
- This discriminator does not run `audio play`, route writes, SET-cal ioctls, PCM, or playback.
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.
