# Native Init V3073 DOOMGENERIC Stutter Cause Audit

## Summary

- Cycle: `V3073`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3073-doomgeneric-stutter-cause-audit`
- Result: PASS, analysis-only.
- Flashed artifact: none in this iteration.
- Resident during audit: `A90 Linux init 0.10.93 (v3071-doomgeneric-frame-timing)`.
- Prior committed probe: `395d0047 Add V3071 DOOM frame timing probe`.

## Safety

- No boot image was built or flashed in this iteration.
- No forbidden partition was touched.
- No raw partition command was used.
- No Wi-Fi credential action was attempted.
- Public report redacts host/device IP, MAC, interface, UUID, and serial identifiers.

## Health And Transport

- Serial bridge was managed and reachable.
- Resident version matched V3071.
- `selftest verbose` returned `pass=12 warn=1 fail=0`.
- Continuous DOOM loop was active before the audit.
- Host NCM readiness was present after route preflight, with identifiers redacted here.
- UDP input over NCM advanced the device input-state from the previous sequence to a newer all-up state.
- DOOM loop remained active after the UDP input check.

## Additional Timing Sample

The continuous loop was stopped cleanly, a foreground bounded timing sample was run, and the continuous loop was restarted afterward.

Foreground `video demo doom loop 180 --wad runtime-private --sha256 EXPECTED` passed with:

- `frames_presented=121`
- `poll_count=184`
- `helper_done=1`
- `display.rc=0`
- `loop.rc=0`
- `presenter.buffer_allocations=1`

Stage timing, in microseconds:

| Stage | Average | Max |
| --- | ---: | ---: |
| alloc | 1 | 18 |
| frame-file read | 497 | 957 |
| KMS begin | 3011 | 3082 |
| dashboard/draw | 26336 | 454916 |
| KMS present | 12834 | 16095 |
| total | 42680 | 462781 |

## Process And Stack Probe

- CPU was mostly idle during active DOOM playback.
- Presenter process was around low single-digit CPU usage, and the DOOM engine was also low single-digit CPU usage.
- Presenter `wchan` was `kthread_flush_work`.
- Presenter stack included `msm_atomic_commit`, `drm_atomic_commit`, and `drm_mode_setcrtc`.
- Engine `wchan` was `hrtimer_nanosleep`.

## Audio Check

- Audio core status remained healthy.
- The DOOM loop starts the existing safe `native-audio-corun-tone` path.
- The current path is not real DOOM SFX/music; it is a bounded 10 second safe tone.
- Audio worker status showed the tone worker completed with `rc=0`.

## Interpretation

The extra timing sample makes the stutter source clearer than the earlier 90-frame run:

1. The raw 1MB frame-file IPC path is not the bottleneck. Read time stayed below `1ms` max in this audit.
2. The DOOM engine itself is not CPU-bound. It sleeps between frames, and overall CPU is mostly idle.
3. The presenter cannot consistently keep up with the helper frame cadence. In the 180-frame helper run, only 121 frames were presented before helper completion.
4. The highest-priority rendering issue is the native dashboard draw path. It fully clears and redraws the DOOM frame, panels, metrics, and input log every presented frame. The max draw time reached about `455ms`.
5. KMS present is a secondary fixed cost. The current DOOM path presents via `DRM_IOCTL_MODE_SETCRTC`, not pageflip, and costs about `13-16ms` per presented frame.
6. Because the presenter reads the latest frame artifact rather than a queued frame stream, any draw/present overrun skips visible animation states and feels like stutter.

## Next Candidate

The next highest-value bounded iteration should target dashboard/presenter pacing, not frame-file IPC.

Recommended order:

1. Add a no-dashboard or minimal-dashboard comparison mode using the same V3071 timing probe to prove the dashboard draw delta live.
2. Replace full-dashboard repaint with a cheaper presentation path: DOOM frame every frame, static dashboard background reused, metrics/input text repainted at a lower cadence or only on change.
3. Move DOOM presenter present mode from per-frame `SETCRTC` toward the already available pageflip path, after draw cost is reduced.
4. Keep NCM host route preflight before judging input responsiveness after any reboot or USB re-enumeration.
