# Native Init V2962 Bad Apple SetCrtc Full-Run Slowdown

## Summary

V2962 ran the full-length Bad Apple player-HUD path on the V2960 resident image. The run proved that audio and frame presentation completed, but it also exposed the performance regression that the operator observed as visible frame stutter: setcrtc mode did not drop frames and the Player HUD render path was too expensive over the full song.

## Scope

- Resident image: `A90 Linux init 0.10.56 (v2960-badapple-setcrtc-default)`
- Run directory: `workspace/private/runs/video/v2962-badapple-setcrtc-full-live-20260620-115854`
- Video route: `DEMO > Bad Apple`, `present=setcrtc`, `layout=player-hud`
- Audio route: full `232090ms` Bad Apple audio, gain `780`
- Safety: no PMIC, backlight, raw DSI, partition, or private payload writes; private logs only

## Observed Counters

| Counter | Value |
| --- | ---: |
| `video.stream.frames_total` | `6962` |
| `video.stream.presented` | `6962` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `275084111145` |
| `video.stream.fps_milli` | `25308` |
| `video.stream.present_mode` | `setcrtc` |
| `video.stream.layout` | `player-hud` |
| `video.stream.beat_flash.active_frames` | `1643` |
| `video.stream.audio_sync.initial_drop_late_ns` | `0` |
| `audio.play.worker.frames_done` | `11140320` |
| `audio.play.worker.bytes_done` | `44561280` |
| `audio.play.worker.done` | `1` |
| `audio.play.worker.rc` | `0` |
| `selftest.fail` | `0` |

## Interpretation

- The video player presented every source frame, so this was not a frame-availability or SD-cache failure.
- The full video pass took about `275.084s` for a `232.09s` audio track, equivalent to about `25.308fps` instead of the target `30fps`.
- Because setcrtc mode did not use the pageflip late-frame drop path, it accumulated visible drift/stutter instead of dropping late frames.
- The likely hot path was per-frame Player HUD repaint work, especially the full lower dashboard and static text regions.

## Decision

Treat V2962 as a valid failure/diagnostic run, not a Bad Apple DoD pass. The next unit should reduce Player HUD per-frame render cost while preserving the read-only dashboard, beat flash, A/V lamp, and setcrtc fallback path.
