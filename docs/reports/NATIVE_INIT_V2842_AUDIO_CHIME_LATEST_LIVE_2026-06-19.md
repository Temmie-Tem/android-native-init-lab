# Native Init V2842 Audio Late Manifest Wait Live Handoff

## Summary

- Cycle: `V2842`
- Track: post-promotion audio 0.10.11 chime playback regression validation.
- Decision: `v2842-late-manifest-play-pass-before-rollback`
- Result directory: `workspace/private/runs/audio/v2842-audio-late-manifest-wait-20260619-152903`
- Candidate tag/version: `v2840-audio-chime-screen` / `0.10.11`
- Candidate image SHA256: `57a61bf47f5da326d7faf6a9fcf1284accf6f9628b4a8bb25679a670c31dbb58`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Late-Manifest Evidence

- Native command started before ACDB deploy: `audio chime --duration-ms 1200 --amplitude-milli 80 --execute`
- Play start rc: `0`
- Card ready after play start: `1` after `2` polls
- Card poll last summary: `{"dev_snd_line": "audio.dev_snd.count=61 control_like=1 pcm_like=59", "has_adsp_rpmsg": true, "has_sound_card": true, "has_sound_control": true, "no_soundcards": false, "proc_asound_cards_line": "audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card", "rpmsg_line": "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0", "sound_class_line": "audio.sound_class.count=128 card_like=1 control_like=1"}`
- Card/control after late deploy before worker done: `1 / 1`
- Manifest wait started/ready/timeout: `1 / 1 / 0`

## Playback Evidence

- Worker status done/attempts: `1` / `1`
- Worker status stdout: `workspace/private/runs/audio/v2842-audio-late-manifest-wait-20260619-152903/37_candidate-audio-play-status-01.txt`
- Worker log stdout: `workspace/private/runs/audio/v2842-audio-late-manifest-wait-20260619-152903/38_candidate-audio-late-manifest-play-log.txt`
- Worker started/done: `1` / `1`
- Integrated done: `1`
- Sound-control ready/timeout: `1` / `0`
- SET-cal hold/all-set/dealloc: `1 / 1 / 1`
- Route apply/reset OK: `1 / 1`
- PCM write/done: `1 / 1`
- Safety amplitude/duration cap: `1 / 1`

## Runtime Artifacts

- Deploy plan: `workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json`
- Remapped remote root: `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe`
- Native manifest remote path: `/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest`
- Native manifest SHA256: `a4f52ce8e8e48a224bd1f5084bb1feebd898c2ce21ce93db605f3f49d3a785b8`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/00-set-arg-cal39-core-custom-topologies.bin`
- `payload` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/00-payload-cal39-core-custom-topologies.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/01-set-arg-cal20-realhal-01.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/02-set-arg-cal20-realhal-02.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/03-set-arg-cal13.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/04-set-arg-cal09.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/05-set-arg-cal11.bin`
- `payload` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/05-payload-cal11.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/06-set-arg-cal12.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/07-set-arg-cal15.bin`
- `payload` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/07-payload-cal15.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/08-set-arg-cal23.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/09-set-arg-cal16.bin`
- `payload` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/09-payload-cal16.bin`
- `set_arg` `/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/10-set-arg-cal21.bin`
- `native_manifest` `/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; runtime ACDB files are staged under `/cache` after sound-card publication.
- No forbidden partitions are touched.
- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).
- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.

## Latest Chime Playback Evidence

- Native command: `audio chime --duration-ms 1200 --amplitude-milli 80 --execute`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2840_audio_chime_screen.img`
- Candidate version/tag: `0.10.11` / `v2840-audio-chime-screen`
- Chime default amplitude milli: `80`
- Chime default duration ms: `1200`
- Boot autoplay: `disabled`.
- This is a playback regression validation for the latest `0.10.11` chime-screen image; it does not enable boot-time audio.
