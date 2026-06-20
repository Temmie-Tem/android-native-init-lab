# Native Init V2953 Bad Apple Player HUD Fastpath Live

## Summary

- Cycle: `V2953`
- Track: active Video playback pipeline / Bad Apple Player HUD.
- Device image: `A90 Linux init 0.10.52 (v2952-badapple-player-hud-fastpath)`
- Boot SHA256: `66906bb692cca6ba366c28bfbb64840f1e7eb573b2ec9e3bd2d56540f7e9971a`
- Decision: `v2953-badapple-player-hud-fastpath-live-pass`
- Result: PASS
- Rollback target: `v2321-usb-clean-identity-rodata`

## Why This Unit Ran

The V2950 display-owner patch stopped background `autohud` ownership, but the
operator observed visible frame stutter during full-song Bad Apple playback. Live
metrics confirmed the observation: V2950 full-song sync presented only 2291 of
6962 frames, dropped 4671 frames, and ran at about 9.8 fps while audio completed.

V2952 adds a Player HUD render fastpath:

- `video` remains `CMD_DISPLAY`, so it stops `autohud` before display playback.
- `video.status.player_hud_fastpath=1` marks the optimized path.
- `mono1` scaled expansion writes one scaled row then duplicates vertical scale
  rows with `memcpy`.
- Player HUD no longer clears the full 1080x2400 framebuffer every frame after
  the first two render calls; it clears only the dynamic regions needed for the
  video/HUD layout.

## Device Validation

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash/readback SHA matched: `66906bb692cca6ba366c28bfbb64840f1e7eb573b2ec9e3bd2d56540f7e9971a`
- Boot verification: `version/status` passed.
- Selftest after playback: `fail=0`.
- Final status: `autohud: stopped`.

## Throughput Comparison

| Route | Frames | Presented | Dropped | FPS | Flip Avg | Max Late |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2950 `player-hud pageflip`, no sync | 900 | 900 | 0 | 22.279 | 44.449 ms | 10.662 s |
| V2952 `player-hud pageflip`, no sync | 300 | 300 | 0 | 30.066 | 33.122 ms | 74.164 ms |
| V2952 `player-hud pageflip`, no sync | 900 | 900 | 0 | 30.029 | 33.276 ms | 54.967 ms |

## Full-Song A/V Sync Result

Command shape:

- Audio: `audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 150 --pcm-gain-milli 840 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute`
- Video: `video demo badapple play --trust-cache --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450`

Markers:

- `video.stream.presented=6962`
- `video.stream.frames_total=6962`
- `video.stream.dropped_frames=0`
- `video.stream.fps_milli=30002`
- `video.stream.elapsed_ns=232048658922`
- `video.stream.flip_events=6962`
- `video.stream.flip_delta_avg_us=33334`
- `video.stream.flip_delta_target_us=33333`
- `video.stream.flip_delta_min_us=16615`
- `video.stream.flip_delta_max_us=49882`
- `video.stream.max_late_ns=33562115`
- `video.stream.audio_sync.initial_drop_late_ns=0`
- `video.stream.beat_flash.active_frames=1643`
- `audio.play.worker.frames_done=11140320`
- `audio.play.worker.bytes_done=44561280`
- `audio.play.worker.done=1 rc=0`

## Interpretation

- The V2950 stutter was not caused by audio or cache I/O. It was a Player HUD
  render-throughput limit.
- V2952 removes the throughput bottleneck for the current 480x360 mono1 Player
  HUD asset: short probes and full-song playback both meet 30 fps pacing.
- The full-song Bad Apple Player HUD path now satisfies the objective playback
  criteria for this asset: all 6962 frames presented, zero dropped frames,
  audio worker completion, beat-flash activity, and post-run `selftest fail=0`.
- Audio volume was not changed in this unit; it remains `amplitude_milli=150` and
  `pcm_gain_milli=840`.

## Safety

- No raw frames, PCM, boot images, or private logs are committed.
- No Wi-Fi, PMIC, GPIO, regulator, GDSC, raw DSI, or backlight paths were used.
- Device changes were limited to the checked boot flash helper and the V2952 boot
  image.
