# Native Init V2964 Bad Apple Incremental HUD Full Live Validation

## Summary

V2964 validated the V2963 incremental Player HUD image on device. The change fixed the V2962 full-song slowdown: the full Bad Apple stream presented all frames with no drops, audio completed, and the video elapsed time returned to the expected 30fps cadence.

## Artifact Under Test

- Native init: `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`
- Build tag: `v2963-badapple-hud-incremental-panel`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2963_badapple_hud_incremental_panel.img`
- Boot SHA-256: `ea35fd8ffdcedee49ba79b2d4a7cf8800655706878d8200a868213b826910dd6`
- Source-build report: `docs/reports/NATIVE_INIT_V2963_BADAPPLE_HUD_INCREMENTAL_PANEL_SOURCE_BUILD_2026-06-20.md`

## Change Under Test

The Player HUD render path now keeps the static dashboard panel persistent between periodic full repaints, while still redrawing the live frame, progress bar, A/V sync lamp, beat flash state, and refreshed `/proc` + `/sys` telemetry. The public status marker was bumped to `video.status.version=7` and exports `video.status.player_hud_incremental_panel=1`.

## Smoke Run

- Run directory: `workspace/private/runs/video/v2964-badapple-hud-incremental-smoke-20260620-121000`
- Duration: first `900` frames / 30s smoke
- Result: `presented=900`, `dropped_frames=0`, `elapsed_ns=29967618947`, `fps_milli=30032`
- Audio: `audio.play.worker.done=1`, `audio.play.worker.rc=0`
- Note: the initial `video status` parser saw a serial marker boundary issue, but the captured output still contained `video.status.version=7` and `video.status.player_hud_incremental_panel=1`; playback validation continued and passed.

## Full-Run Counters

- Run directory: `workspace/private/runs/video/v2964-badapple-hud-incremental-full-20260620-121108`

| Counter | Value |
| --- | ---: |
| `video.stream.frames_total` | `6962` |
| `video.stream.presented` | `6962` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `232228888140` |
| `video.stream.fps_milli` | `29979` |
| `video.stream.mbps_milli` | `647` |
| `video.stream.max_late_ns` | `209864607` |
| `video.stream.present_mode` | `setcrtc` |
| `video.stream.layout` | `player-hud` |
| `video.stream.beat_flash.active_frames` | `1643` |
| `video.stream.beat_flash.first_frame` | `39` |
| `video.stream.beat_flash.last_frame` | `5933` |
| `video.stream.audio_sync.initial_drop_late_ns` | `0` |
| `audio.play.worker.frames_done` | `11140320` |
| `audio.play.worker.bytes_done` | `44561280` |
| `audio.play.worker.done` | `1` |
| `audio.play.worker.rc` | `0` |
| `selftest.fail` | `0` |

## V2962 to V2964 Delta

| Metric | V2962 | V2964 | Result |
| --- | ---: | ---: | --- |
| Presented / total | `6962 / 6962` | `6962 / 6962` | unchanged pass |
| Dropped frames | `0` | `0` | unchanged pass |
| Full stream elapsed | `275.084s` | `232.229s` | fixed slowdown |
| Effective FPS | `25.308` | `29.979` | restored 30fps cadence |
| Audio worker | `done rc=0` | `done rc=0` | unchanged pass |
| Selftest | `fail=0` | `fail=0` | unchanged pass |

## Decision

V2963/V2964 fixes the Player HUD full-run performance regression seen in V2962. This is a valid rollback/baseline candidate for the Bad Apple player-HUD route, subject to the operator's final visual/audio sync acceptance. Raw logs and media payloads remain private and were not committed.
