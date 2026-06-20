# Native Init V2968 Bad Apple V2963 Post-Reject Revalidation

## Summary

After rejecting the V2965 lower-volume candidate, the device was restored to the accepted V2963 incremental Player HUD image and the full-length Bad Apple A/V path was re-run. V2968 reproduced the V2964 full-run cadence: all frames presented, no drops, full stream time near the 232 s audio duration, audio worker completed, and selftest remained `fail=0`.

## Artifact Under Test

- Native init: `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2963_badapple_hud_incremental_panel.img`
- Boot SHA-256: `ea35fd8ffdcedee49ba79b2d4a7cf8800655706878d8200a868213b826910dd6`
- Run directory: `workspace/private/runs/video/v2968-badapple-v2963-post-reject-full-20260620-124159`

## Command Shape

- Audio: `audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 150 --pcm-gain-milli 780 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute`
- Video: `video demo badapple play --trust-cache --present setcrtc --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450`

## Counters

| Counter | Value |
| --- | ---: |
| `video.stream.frames_total` | `6962` |
| `video.stream.presented` | `6962` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `232225445276` |
| `video.stream.fps_milli` | `29979` |
| `video.stream.max_late_ns` | `205066537` |
| `video.stream.present_mode` | `setcrtc` |
| `video.stream.layout` | `player-hud` |
| `video.stream.beat_flash.active_frames` | `1643` |
| `video.stream.beat_flash.first_frame` | `39` |
| `video.stream.beat_flash.last_frame` | `5933` |
| `video.stream.audio_sync.initial_drop_late_ns` | `0` |
| `audio.play.worker.pcm_gain_milli` | `780` |
| `audio.play.worker.frames_done` | `11140320` |
| `audio.play.worker.bytes_done` | `44561280` |
| `audio.play.worker.done` | `1` |
| `audio.play.worker.rc` | `0` |
| `selftest.fail` | `0` |

## Comparison

| Metric | V2964 | V2968 |
| --- | ---: | ---: |
| Presented / total | `6962 / 6962` | `6962 / 6962` |
| Dropped frames | `0` | `0` |
| Full stream elapsed | `232.229s` | `232.225s` |
| Effective FPS | `29.979` | `29.979` |
| Max late | `0.210s` | `0.205s` |
| Audio worker | `done rc=0` | `done rc=0` |
| Selftest | `fail=0` | `fail=0` |

## Decision

V2963 remains the current accepted Bad Apple Player HUD candidate. The failed V2965 lower-gain experiment did not identify a persistent V2963 cadence problem; after rollback, V2963 reproduced the stable full-song timing. Do not retry volume trim as a default until the next attempt includes a cadence guard or playback-mode/pacing discriminator.
