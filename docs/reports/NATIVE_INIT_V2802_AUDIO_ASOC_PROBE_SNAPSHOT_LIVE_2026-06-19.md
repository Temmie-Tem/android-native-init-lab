# Native Init V2802 Audio ASoC Probe Snapshot Live Handoff

## Summary

- Cycle: `V2802`
- Track: audio ADSP/APR-up to ALSA/ASoC publication frontier.
- Decision: `v2802-audio-asoc-probe-snapshot-card-present-before-rollback`
- Result directory: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839`
- Candidate tag: `v2799-audio-native-ioctl-width`
- Candidate image SHA256: `f07afce570a52b5c9fa59e16932d16b4f83d258b58a2a738e96ce42003ee4e6b`
- ADSP boot rc: `0` accepted=`1`
- Sound ready after ADSP: `1`
- Rollback attempted: `1`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Status Summary

- Before ADSP: rpmsg=`audio.rpmsg.count=0 adsp_like=0 cdsp_like=0` sound=`audio.sound_class.count=1 card_like=0 control_like=0` cards=`audio.proc_asound_cards=--- no soundcards ---`
- After ADSP: rpmsg=`audio.rpmsg.count=20 adsp_like=7 cdsp_like=0` sound=`audio.sound_class.count=128 card_like=1 control_like=1` cards=`audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card`
- Poll 1: sound_card=`1` sound_control=`1` path=`workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/14_candidate-audio-adsp-status-poll-01.txt`

## Live Classification

- Direct foreground `audio adsp-boot-once` on the same `v2799-audio-native-ioctl-width` candidate publishes the `sm8150-tavil-snd-card` card and `/dev/snd/controlC0` by the first post-ADSP poll.
- This rejects an ADSP/PIL/APR/ASoC publication regression as the explanation for V2799/V2800/V2801 integrated-play timeouts.
- The remaining blocker is localized to the integrated `audio play --execute` path before or around its async worker/deploy/order boundary: the worker waited 70 s for sound-control readiness even though the same image can publish the card through a direct foreground ADSP boot.
- Next unit should make the native play path prime ADSP/sound publication in the foreground before the async playback worker, then retest the full integrated sequence through ACDB SET replay and bounded PCM.

## Snapshot Paths

- Before ADSP full dmesg: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/08_candidate-before-adsp-dmesg_full.txt`
- After ADSP full dmesg: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/17_candidate-after-adsp-dmesg_full.txt`
- Before ADSP platform audio snapshot: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/10_candidate-before-adsp-platform_audio.txt`
- After ADSP platform audio snapshot: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/19_candidate-after-adsp-platform_audio.txt`
- Before ADSP debug ASoC snapshot: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/11_candidate-before-adsp-debug_asoc.txt`
- After ADSP debug ASoC snapshot: `workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-20260619-093839/20_candidate-after-adsp-debug_asoc.txt`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed; no ACDB SET-cal, route, PCM, mixer, or playback command is issued.
- The single live mutation inside the candidate boot is the already-token-gated ADSP boot write, followed by read-only snapshots.
- Rollback target is `v2321`; public report is metadata-only.
