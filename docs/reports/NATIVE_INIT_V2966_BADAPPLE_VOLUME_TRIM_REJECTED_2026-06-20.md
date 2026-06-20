# Native Init V2966 Bad Apple Volume Trim Candidate Rejected

## Summary

V2965 tested a small Bad Apple menu volume reduction (`pcm_gain_milli=780` → `720`) on top of the V2963 incremental Player HUD image. The candidate booted and the 30 s smoke pass was clean, but two full-length runs regressed video cadence compared with V2964. The volume-trim source delta is therefore rejected for now and must not replace the V2963 baseline candidate.

## Candidate Under Test

- Native init: `A90 Linux init 0.10.58 (v2965-badapple-volume-trim)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2965_badapple_volume_trim.img`
- Boot SHA-256: `41464e82e4e823b54219fb9b7fb74af1c54a0c8f74044847653be1b0bc87abe3`
- Change: APPS/DEMO Bad Apple audio command `--pcm-gain-milli 720`
- Parent accepted candidate: `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`

## Pre-Flash Safety

Rollback artifacts were present and SHA-checked before flashing:

- `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- `boot_linux_v48.img`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`

Flash/readback/boot verification for V2965 passed through `native_init_flash.py`.

## Static Validation

- `python3 -m py_compile` for the V2965 builder and affected tests: PASS
- `python3 -m unittest` for V2965 plus V2963/V2960/V2952 related tests: PASS, 9 tests
- Build warnings: existing warning class only; build exited 0

## Live Evidence

### V2966 Smoke

- Run directory: `workspace/private/runs/video/v2966-badapple-volume-trim-smoke-20260620-122620`
- Audio command accepted `pcm_gain_milli=720`; worker status later reported `done=1 rc=0`
- Video command: 900 frames, `present=setcrtc`, `layout=player-hud`

| Counter | Value |
| --- | ---: |
| `video.stream.frames_requested` | `900` |
| `video.stream.presented` | `900` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `29980741760` |
| `video.stream.fps_milli` | `30019` |
| `video.stream.max_late_ns` | `199753764` |
| `audio.play.worker.pcm_gain_milli` | `720` |
| `audio.play.worker.done` | `1` |
| `audio.play.worker.rc` | `0` |
| `selftest.fail` | `0` |

### V2966 Full Run

- Run directory: `workspace/private/runs/video/v2966-badapple-volume-trim-full-20260620-122739`

| Counter | Value |
| --- | ---: |
| `video.stream.frames_total` | `6962` |
| `video.stream.presented` | `6962` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `241197556158` |
| `video.stream.fps_milli` | `28864` |
| `video.stream.max_late_ns` | `9168752176` |
| `audio.play.worker.pcm_gain_milli` | `720` |
| `audio.play.worker.done` | `1` |
| `audio.play.worker.rc` | `0` |
| `selftest.fail` | `0` |

### V2967 Full Rerun

- Run directory: `workspace/private/runs/video/v2967-badapple-volume-trim-full-rerun-20260620-123212`
- The host-side `a90ctl` timeout/marker handling overlapped the tail of the long video command, but the final video counters were recovered from the serial output.

| Counter | Value |
| --- | ---: |
| `video.stream.frames_total` | `6962` |
| `video.stream.presented` | `6962` |
| `video.stream.dropped_frames` | `0` |
| `video.stream.elapsed_ns` | `355800389656` |
| `video.stream.fps_milli` | `19567` |
| `video.stream.max_late_ns` | `123768659320` |
| `audio.play.worker.pcm_gain_milli` | `720` |

## Comparison With Accepted V2964

| Metric | V2964 | V2966 full | V2967 rerun |
| --- | ---: | ---: | ---: |
| Presented / total | `6962 / 6962` | `6962 / 6962` | `6962 / 6962` |
| Dropped frames | `0` | `0` | `0` |
| Full stream elapsed | `232.229s` | `241.198s` | `355.800s` |
| Effective FPS | `29.979` | `28.864` | `19.567` |
| Max late | `0.210s` | `9.169s` | `123.769s` |

## Decision

Reject V2965 as a baseline candidate. The requested volume trim is valid as an operator-facing preference, but it cannot be merged as the default until the full-song cadence remains at the V2964 level. The source tree is restored to the committed V2963 default (`pcm_gain_milli=780`) after recording this failed live discriminator.


## Recovery

After rejecting the V2965 candidate, the device was flashed back to the accepted V2963 image through `native_init_flash.py`:

- Restored image: `workspace/private/inputs/boot_images/boot_linux_v2963_badapple_hud_incremental_panel.img`
- Restored SHA-256: `ea35fd8ffdcedee49ba79b2d4a7cf8800655706878d8200a868213b826910dd6`
- Post-restore version: `A90 Linux init 0.10.57 (v2963-badapple-hud-incremental-panel)`
- Post-restore status: `selftest fail=0`

## Next Step

Continue from V2963. If volume trim is retried, first isolate the full-run cadence instability with a playback-mode comparison or an explicit pacing/prefetch change; do not ship a lower-gain default on evidence that regresses the full-length Bad Apple timing.
