# Native Init V2848 Audio Stop Execute Live Handoff

## Summary

- Cycle: `V2848`
- Track: post-promotion bounded audio stop execute validation.
- Decision: `v2848-stop-execute-pass-before-rollback`
- Result directory: `workspace/private/runs/audio/v2848-audio-late-manifest-wait-20260619-162757`
- Candidate tag/version: `v2847-audio-stop-execute` / `0.10.14`
- Candidate image SHA256: `23b54b37bc3451697d218ddbd3d162ec3b167427b460bc0f31d40f17c55abd6e`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Stop Execute Evidence

- Command: `audio stop internal-speaker-safe --execute`
- Stop rc: `0`
- Stop stdout: `workspace/private/runs/audio/v2848-audio-late-manifest-wait-20260619-162757/14_candidate-audio-stop-execute.txt`
- Execute supported/requested: `1` / `1`
- No-active playback/SET-cal markers: `1` / `1`
- Route reset mode/core/write-done: `1` / `1` / `1`
- Stop done/pass: `1` / `1`
- Refused/error/write-failed: `0` / `0` / `0`

## Boot Chime Settle

- Boot chime launch log: `/cache/a90-audio-play/boot-chime-launch.log`
- Boot chime launch log stdout: `workspace/private/runs/audio/v2848-audio-late-manifest-wait-20260619-162757/09_candidate-audio-boot-chime-launch-log-before-stop.txt`
- Boot chime started markers: `1`
- Worker done before stop/attempts: `1` / `1`
- Worker status stdout: `workspace/private/runs/audio/v2848-audio-late-manifest-wait-20260619-162757/10_candidate-audio-play-status-01.txt`
- Worker log stdout: `workspace/private/runs/audio/v2848-audio-late-manifest-wait-20260619-162757/11_candidate-audio-worker-log-before-stop.txt`
- Card ready before stop: `1` after `1` polls
- Card poll last summary: `{"dev_snd_line": "audio.dev_snd.count=61 control_like=1 pcm_like=59", "has_adsp_rpmsg": true, "has_sound_card": true, "has_sound_control": true, "no_soundcards": false, "proc_asound_cards_line": "audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card", "rpmsg_line": "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0", "sound_class_line": "audio.sound_class.count=128 card_like=1 control_like=1"}`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; no host runtime artifacts are copied in this unit.
- The runner issues no PCM playback command; the only active command is one `audio stop --execute`.
- Stop execute is expected to write only the already-reviewed core route reset controls.
- No ACDB deallocate or fake PCM stop is attempted without an active native session.
- Public report is metadata-only; private raw command transcripts stay under `workspace/private/`.
