# Native Init V3076 DOOMGENERIC Remaining Causes Audit

## Summary

- Cycle: `V3076`
- Date: `2026-06-23`
- Type: live, non-flash audit on the already-installed V3074 image.
- Resident: `A90 Linux init 0.10.94 (v3074-doomgeneric-minimal-dashboard)`.
- Scope: check for remaining causes of DOOM choppiness after the V3074 minimal-dashboard fix.

No boot image was built or flashed in this audit.

## Starting State

- Managed serial bridge was running.
- DOOM continuous loop was active before the probe.
- `selftest verbose` remained healthy: `pass=12 warn=1 fail=0`.
- `video demo doom status` reported the expected V3074 minimal-dashboard markers:
  - `video.demo.doom.dashboard.profile=minimal-fastdraw`
  - `video.demo.doom.dashboard.redraw=doom-frame-plus-compact-status`
  - `video.demo.doom.dashboard.frame_mode=minimal-dashboard`
  - `video.demo.doom.loop.frame_ms=28`
  - `video.demo.doom.presenter.pacing=helper-frame-mtime`
  - `video.demo.doom.presenter.poll_ms=4`
  - `video.demo.input.active=udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`

## Pageflip Probe

The current resident still has the existing KMS pageflip path available. A non-DOOM
`video flipprobe 120` run completed successfully:

- `video.flipprobe.presented=120`
- `video.flipprobe.frames=120`
- `video.flipprobe.fps_milli=59688`
- `video.flipprobe.flip_events=120`
- `video.flipprobe.ioctl=DRM_IOCTL_MODE_PAGE_FLIP`
- `video.flipprobe.path=kms-dumb-buffer-pageflip`
- command status: `rc=0 status=ok`

Interpretation: the pageflip/vblank path itself is healthy on this resident. This
makes the current DOOM presenter path the stronger suspect, because DOOM still calls
`a90_kms_present("doomdash", false)`, which uses `DRM_IOCTL_MODE_SETCRTC`.

## DOOM Bounded Timing Probe

`video demo doom loop 600 ...` was rejected by the current command parser because
`VIDEO_DEMO_DOOMGENERIC_MAX_FRAMES` is `300`. The maximum bounded sample was then
run with `300` frames and completed successfully:

- `video.demo.doom.loop.frames_presented=300`
- `video.demo.doom.loop.poll_count=1198`
- `video.demo.doom.loop.helper_done=0`
- `video.demo.doom.loop.display.rc=0`
- `video.demo.doom.loop.rc=0`
- `video.demo.doom.loop.presenter.buffer_allocations=1`

Stage timing, in microseconds:

| Stage | Average | Max |
| --- | ---: | ---: |
| alloc | 1 | 17 |
| frame-file read | 483 | 926 |
| KMS begin | 4481 | 4572 |
| dashboard/draw | 808 | 873 |
| KMS present | 7033 | 16878 |
| total | 12807 | 22782 |

Interpretation:

1. The V3074 minimal dashboard remains stable. Draw max stayed below `1ms`.
2. The raw frame-file read path remains below `1ms` max and is not the current bottleneck.
3. The largest remaining timing variance is KMS present/commit, with total frame max
   now dominated by `SETCRTC`-style presentation rather than drawing.
4. The foreground 300-frame probe showed all requested frames, so this was not a helper
   production failure.

## Input And NCM Check

After restarting the continuous DOOM loop, the NCM host route was present and the
USB gadget reported the expected NCM plus ACM functions. A short UDP input packet
sequence was sent to the device input port. The device-side state file then showed
the final all-up state:

- `seq=1203`
- all DOOM roles `0`
- `active=0`

Interpretation: the UDP/NCM input path is working in the current continuous loop.
The earlier route repair requirement remains operationally relevant after reboot or
USB re-enumeration, but it was not failing during this audit.

## Operational Issue Observed

Serial control-plane character loss reproduced during a `run /bin/busybox ...` command:
the device received a path missing one character. Restarting the managed bridge fixed
the immediate issue, and the same short command succeeded afterward.

Interpretation: this does not explain visual choppiness or UDP input latency, but it is
still a real demo/validation hazard for serial commands. Keep command validation
sequential, avoid back-to-back long serial command bursts, and restart the managed bridge
when command text is visibly corrupted.

## Suspect Ranking After V3076

1. **DOOM presenter still uses SETCRTC instead of pageflip.** Pageflip probe is healthy,
   while DOOM timing shows remaining present/total variance in the SETCRTC path.
2. **DOOM lacks pageflip/vblank cadence control.** The presenter is still polling the
   helper frame file and presenting immediately, not scheduling to display vblank.
3. **Bounded-loop max-frame cap is too low for longer diagnostics.** The current parser
   caps foreground timing at `300` frames, which is enough for a short probe but not a
   long soak-style jitter histogram.
4. **Serial bridge fragility remains.** This affects validation/control reliability, not
   the UDP input gameplay path.
5. **Real DOOM audio is not implemented.** The current loop only starts the safe bounded
   native tone co-run, so lack of continuous SFX/music is expected behavior rather than a
   runtime failure.

## Recommended Next Iteration

Build the next V-iteration around DOOM pageflip presentation:

- Add an optional DOOM presenter pageflip mode that calls `a90_kms_present_pageflip()`.
- Print flip event counters and flip delta min/avg/max for DOOM, similar to the existing
  stream player telemetry.
- Keep the current SETCRTC path as fallback.
- Keep V3074 minimal-dashboard drawing unchanged so the next comparison isolates the
  present/cadence change.
- Consider raising the foreground DOOM timing cap for diagnostics only, or adding a
  separate long-sample timing command that does not enlarge normal demo command scope.

## Safety

- No flash was performed.
- No forbidden partition was touched.
- Runtime changes were limited to stopping/restarting the DOOM loop, pageflip probing,
  UDP input probing, and restarting the managed serial bridge.
