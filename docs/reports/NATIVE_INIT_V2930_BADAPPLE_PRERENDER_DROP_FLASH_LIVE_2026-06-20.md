# Native Init V2930 Bad Apple Pre-Render Drop Skip Flash/Live

## Summary

- Cycle: `V2930`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2930-badapple-prerender-drop-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v2929_badapple_prerender_drop.img`
- Boot SHA256: `cddb4ad1ac07f95e0c2a36bff9e16557bc11540ae3d38edc5b735130577d7d18`
- Init after flash: `A90 Linux init 0.10.43 (v2929-badapple-prerender-drop)`

## Why This Unit Existed

- The first 10 second Bad Apple probe on the prior V2927 route collapsed after extending the preview window.
- V2927 evidence: `workspace/private/runs/video/v2929-badapple-10s-audibility-probe-20260620-084237/live.log`.
- V2927 result: `presented=38`, `frames_requested=300`, `dropped_frames=262`, `initial_drop_late_ns=373568697`, `flip_delta_avg_us=258094`.
- Root cause: the late-drop decision happened after payload read, render, and KMS begin; dropped frames still consumed full render cost, so a long run could not catch up.

## Implemented Fix

- Added `video_skip_exact_fd()` to skip a late frame payload without rendering it.
- Moved the late-frame drop decision to immediately after reading the frame record and before KMS/render work.
- Preserved the one-frame threshold policy: a frame is skipped only when more than one frame interval late.

## Live Validation

- Run: `workspace/private/runs/video/v2929-badapple-prerender-drop-live-20260620-084725/live.log`.
- Command shape: audio worker plus 10 second / 300 frame Bad Apple Player HUD run.
- Result: `video.stream.presented=300`, `video.stream.frames_requested=300`, `video.stream.dropped_frames=0`.
- Sync markers: `video.stream.audio_sync.start_offset_ms=450`, `video.stream.audio_sync.initial_drop_late_ns=0`.
- Timing: `video.stream.fps_milli=30060`, `video.stream.flip_delta_avg_us=33337`.
- Audio worker: `audio.play.worker.done=1 rc=0`, `frames_done=480000`, `bytes_done=1920000`.
- Final health: `selftest fail=0`.

## Audio Note

- The operator later reported that Bad Apple video was visible but audio was not heard on the device during a preview attempt.
- This V2930 unit proves the software audio worker completed and PCM bytes were written; it does not claim physical Bad Apple audibility.
- Physical audibility remains a separate operator-confirmed gate per `GOAL.md`.

## Safety

- Boot partition only via `native_init_flash.py`.
- Rollback images were present before flashing.
- No Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, or GDSC writes.
- Audio stayed on the known internal-speaker-safe route with amplitude cap `<=0.2`.
