# Native Init V2932 Bad Apple Long Preview Flash/Live

## Summary

- Cycle: `V2932`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Decision: `v2932-badapple-long-preview-live-pass-with-audio-audibility-pending`
- Result: PASS for boot, health, 10 second video presentation, and audio worker completion; physical audio audibility remains pending operator confirmation.
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v2931_badapple_long_preview.img`
- Boot SHA256: `c9c0341fb16541614ce3f2e67b6d118b06c362969a968863af51d684e42788e7`
- Init after flash: `A90 Linux init 0.10.44 (v2931-badapple-long-preview)`

## Flash / Health

- Rollback images verified before flash:
  - `v2321`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `v2237`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `v48`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Readback SHA matched the requested V2931 image.
- Post-boot `version`/`status` passed.
- Final `selftest verbose`: `pass=12 warn=1 fail=0`.

## Live Validation

- Passing run: `workspace/private/runs/video/v2932-badapple-long-preview-live-timeout45-20260620-085825/live.log`.
- Command shape: audio worker started, then video launched immediately with `--timeout 45` to avoid host-side serial timeout during the 10 second no-output window.
- Video result: `video.stream.presented=300`, `video.stream.frames_requested=300`, `video.stream.dropped_frames=0`.
- Presentation ratio: `300/300 = 1.000`, meeting the short-preview DOD threshold of `>=0.95` for this bounded validation.
- Sync markers: `video.stream.audio_sync.start_offset_ms=450`, `first_presented_frame=0`, `initial_drop_late_ns=0`.
- Timing: `video.stream.fps_milli=30051`, `flip_delta_avg_us=33340`, `flip_delta_target_us=33333`, `max_late_ns=44973547`.
- Audio final status after drain: `audio.play.worker.done=1 rc=0`, `frames_done=480000`, `bytes_done=1920000`.

## Intermediate Runs

- `workspace/private/runs/video/v2932-badapple-long-preview-live-20260620-085605/live.log`: serial END marker corruption during pre-selftest; device recovered with `reattach`, no device fault.
- `workspace/private/runs/video/v2932-badapple-long-preview-live-20260620-085703/live.log`: intentionally too much host-side gap after audio start; result `presented=270/300`, `dropped_frames=30`, `anchor_age_ns=1411100729`, useful as evidence that delayed video start consumes the sync budget.
- `workspace/private/runs/video/v2932-badapple-long-preview-live-tight-20260620-085744/live.log`: reduced gap but host timeout was too short and the command overlapped with the next command; discarded as transport contamination.

## Audio Audibility Status

- The operator reported that Bad Apple video was visible but audio was not heard before this cleanup.
- Additional isolation on V2929 ran bounded chime probes at `160/1000` and `200/1000` amplitude caps; both completed in software with `audio.play.worker.done=1 rc=0`.
- Worker logs show App Type Config write OK, SET-cal replay OK, route apply OK, PCM open/prepare/write/drain OK, route reset OK, and SET-cal deallocate OK.
- This is sufficient to classify the remaining issue as physical audibility / perceived volume / route-output confirmation, not a frame scheduler or PCM-write failure.
- Per `GOAL.md`, the demo is not fully closed until the operator confirms audible Bad Apple audio in sync.

## Safety

- Boot partition only via checked flash helper.
- No forbidden partition writes.
- No Wi-Fi, network, credential, DHCP, route, or ping work.
- No Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, or GDSC writes.
- Audio stayed on the known internal-speaker-safe route with amplitude cap `<=0.2`.
