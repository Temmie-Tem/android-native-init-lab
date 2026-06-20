# Native Init V2937 Bad Apple Preview-Limited Audio Flash Live

## Summary

- Cycle: `V2937`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2937-badapple-preview200-audio-live-pass-audibility-pending`
- Result: PASS for boot, health, preview-limited PCM selection, audio worker completion, and 95%+ Player HUD presentation.
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v2936_badapple_preview200_audio.img`
- Boot SHA256: `c5239e728a32e5c7b96a8ce8762c1e78a88e7a5f12f1554fea3b8bd76fd38bdf`
- Init after flash: `A90 Linux init 0.10.45 (v2936-badapple-preview200-audio)`

## Context

- Operator observed that the previous Bad Apple video was visible but audio was not audible.
- Host analysis showed the original V2903 PCM starts with silence and is quiet in the first preview window.
- A private preview-limited PCM was generated and staged at `/cache/a90-runtime/pkg/av/v2933/audio/badapple_preview200_limited.s16le`.
- The staged PCM SHA256 was verified live as `bf71c3e489dac64923e738a141086b32956ffdcf539e6e576fbb0b306a7a093d`.
- V2936 switches the Bad Apple menu preview's PCM path from the original V2920 PCM to that preview-limited V2933 PCM path.

## Live Evidence

- Flash helper: checked `native_init_flash.py --from-native` path only; boot partition only.
- Flash readback SHA256 matched `c5239e728a32e5c7b96a8ce8762c1e78a88e7a5f12f1554fea3b8bd76fd38bdf`.
- Post-flash `version`/`status` passed and reported `0.10.45` / `v2936-badapple-preview200-audio`.
- Pre-run and final `selftest verbose` reported `fail=0`.
- Run log: `workspace/private/runs/video/v2937-badapple-preview200-menupath-live-20260620-092238/live.log`.

## Player HUD Result

- Command path used the same PCM path now hard-coded into the menu preview.
- Audio worker:
  - `audio.play.worker.pcm_file=/cache/a90-runtime/pkg/av/v2933/audio/badapple_preview200_limited.s16le`
  - `audio.play.worker.frames_done=480000`
  - `audio.play.worker.bytes_done=1920000`
  - `audio.play.worker.done=1 rc=0`
- Video Player HUD:
  - `video.stream.presented=291`
  - `video.stream.frames_requested=300`
  - `video.stream.dropped_frames=9`
  - `video.stream.fps_milli=29178`
  - `video.stream.flip_delta_avg_us=33168`
  - `video.stream.audio_sync.ready=1`
  - `video.stream.audio_sync.first_presented_frame=7`
  - `video.stream.audio_sync.initial_drop_late_ns=260796042`

## Interpretation

- The V2937 host-driven validation passes the 95% presentation bar: `291/300 = 97.0%`.
- The 9 dropped frames are attributed to host-command gap before video start: `anchor_age_ns=710499323` exceeded the 450 ms sync offset before the video command entered the player.
- This is a worse condition than the actual menu handler, which starts audio and video inside one native process without a host round trip.
- A fresh post-reboot manual V2935 run with the same preview-limited PCM and no injected sleep presented `300/300`, `dropped_frames=0`, `fps_milli=30092`, and `flip_delta_avg_us=33168`.
- Earlier warm-state cadence degradation was reproduced as a runtime KMS/display cadence state issue and cleared by reboot plus `stophud`.

## Audibility Status

- Native audio worker completion is proven for both a 3 second 0.2-cap chime and the 10 second preview-limited PCM path.
- Physical audibility remains an operator-listener checkpoint for the Bad Apple music track. The code path is now using the louder preview-limited PCM; if still inaudible, the next unit should inspect speaker route gain/mixer state without raising the amplitude cap or enabling smart-amp boost writes.

## Safety

- No raw DSI, Venus, GPU, PMIC, PWM, regulator, GPIO, GDSC, or backlight writes.
- Audio amplitude stayed within the source-enforced `200` milli cap.
- No Wi-Fi scan/connect/DHCP/ping.
- No credential, raw video stream, raw audio PCM, boot image, or private log is committed.
- Device remains on V2936 after successful health check; rollback target remains V2321.
