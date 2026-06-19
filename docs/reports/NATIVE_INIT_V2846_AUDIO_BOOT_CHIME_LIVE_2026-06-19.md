# Native Init V2846 Audio Boot Chime Live Handoff

## Summary

- Cycle: `V2846`
- Track: post-promotion best-effort audio boot chime validation.
- Decision: `v2846-boot-chime-pass-before-rollback`
- Result directory: `workspace/private/runs/audio/v2846-audio-late-manifest-wait-20260619-160924`
- Candidate tag/version: `v2845-audio-boot-chime` / `0.10.13`
- Candidate image SHA256: `be1e6f2559d435b72cce3d152c905c7b74742f2ba2c6917101d73a80d84f5bda`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`
- Operator audible confirmation: `pending-human-listen-confirmation`

## Boot Chime Evidence

- Manual audio command sent: `0`
- Boot chime launch log: `/cache/a90-audio-play/boot-chime-launch.log`
- Boot chime launch log stdout: `workspace/private/runs/audio/v2846-audio-late-manifest-wait-20260619-160924/09_candidate-audio-boot-chime-launch-log.txt`
- Boot chime started markers: `1`
- Host artifact deployment performed: `0`
- Bundled manifest path: `/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest`
- Bundled root: `/a90/audio/setcal/internal-speaker-safe`
- Card ready after boot chime start: `1` after `1` polls
- Card poll last summary: `{"dev_snd_line": "audio.dev_snd.count=61 control_like=1 pcm_like=59", "has_adsp_rpmsg": true, "has_sound_card": true, "has_sound_control": true, "no_soundcards": false, "proc_asound_cards_line": "audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card", "rpmsg_line": "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0", "sound_class_line": "audio.sound_class.count=128 card_like=1 control_like=1"}`
- Manifest wait started/ready/timeout: `1 / 1 / 0`

## Playback Evidence

- Worker status done/attempts: `1` / `1`
- Worker status stdout: `workspace/private/runs/audio/v2846-audio-late-manifest-wait-20260619-160924/12_candidate-audio-play-status-01.txt`
- Worker log stdout: `workspace/private/runs/audio/v2846-audio-late-manifest-wait-20260619-160924/13_candidate-audio-boot-chime-worker-log.txt`
- Worker started/done: `1` / `1`
- Integrated done: `1`
- Sound-control ready/timeout: `1` / `0`
- SET-cal hold/all-set/dealloc: `1 / 1 / 1`
- Route apply/reset OK: `1 / 1`
- PCM write/done: `1` / `1`
- Safety amplitude/duration cap: `1 / 1`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; no runtime ACDB files are copied from the host in this unit.
- No manual `audio play` or `audio chime` command is sent; this validates PID1 boot autoplay only.
- No forbidden partitions are touched.
- Boot chime uses amplitude `80` milli and duration `1200` ms by default, below the source cap.
- Public report is metadata-only; private raw command transcripts stay under `workspace/private/`.
