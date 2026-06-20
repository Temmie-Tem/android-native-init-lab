# Native Init V2961 Bad Apple Setcrtc Default Live Validation

## Summary

- Cycle: `V2961`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Result: PASS
- Device image: `A90 Linux init 0.10.56 (v2960-badapple-setcrtc-default)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2960_badapple_setcrtc_default.img`
- Boot SHA256: `bb27f5f258fe00c1214d5d2bb061de66fe244160b9bb365cb5d1835a66ad0b8d`
- Private run evidence: `workspace/private/runs/video/v2961-badapple-setcrtc-default-live-20260620-115442`

## Why This Unit Exists

The operator observed visible Bad Apple frame stutter while audio was still correct. The V2954 source delta only reduced Bad Apple menu PCM gain (`840` to `780`), so the stutter was not caused by an audio path change. The pageflip experiments presented every frame but still reported alternating pageflip-event cadence around 16 ms / 50 ms. V2960 therefore changes the APPS/DEMO Bad Apple default present mode to `setcrtc`, leaving direct `--present pageflip` available for manual comparison.

## Live Procedure

- Flashed the V2960 candidate through `workspace/public/src/scripts/revalidation/native_init_flash.py` with expected SHA256 `bb27f5f258fe00c1214d5d2bb061de66fe244160b9bb365cb5d1835a66ad0b8d`.
- Verified native init version/status after boot.
- Started bounded 30 s Bad Apple PCM audio through `audio play internal-speaker-safe --mode listen --duration-ms 30000 --amplitude-milli 150 --pcm-gain-milli 780 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute`.
- Ran the matching 900-frame Player HUD video probe with `video demo badapple play --trust-cache --present setcrtc --layout player-hud --frames 900 --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450`.
- Checked `audio play-status` and `selftest verbose` after playback.

## Key Results

- `video.stream.presented=900`
- `video.stream.frames_requested=900`
- `video.stream.dropped_frames=0`
- `video.stream.elapsed_ns=29971962071`
- `video.stream.fps_milli=30028`
- `video.stream.present_mode=setcrtc`
- `video.stream.layout=player-hud`
- `video.stream.path=kms-dumb-buffer`
- `video.stream.flip_events=0`
- `video.stream.flip_delta_count=0`
- `audio.play.worker.frames_done=1440000`
- `audio.play.worker.bytes_done=5760000`
- `audio.play.worker.done=1 rc=0`
- `selftest: pass=12 warn=1 fail=0`

## Interpretation

- The symptom is consistent with pageflip cadence jitter rather than frame production failure: prior pageflip probes had `dropped_frames=0` but retained 16/50 ms flip-event alternation.
- The setcrtc path keeps the 30 fps target over the bounded A/V probe and removes the pageflip-event cadence surface (`flip_events=0`).
- This is a pragmatic default for the menu-launched demo. Pageflip remains available as an explicit CLI mode for later analysis.
- `video.stream.late_frames=900` is not treated as a drop/failure for this setcrtc probe; setcrtc does not provide pageflip completion timestamps, so the legacy late-frame counter is less meaningful than `presented`, `dropped_frames`, elapsed time, and audio completion.

## Safety

- Only the boot partition was flashed, through the checked helper.
- Rollback images `v2321`, `v2237`, and `v48` were present and SHA-verified before flash.
- No Wi-Fi, network credentials, DHCP, routes, external ping, PMIC, GPIO, GDSC, regulator, backlight, or raw DSI paths were used.
- Generated run logs and boot images remain private/untracked.

## Follow-Up

- If operator-visible stutter persists under the menu default, the next discriminator should be a full-song V2960 setcrtc run with the same counters and human visual feedback.
- If setcrtc is visually smooth, promote the default and leave pageflip as a manual debug mode.
