# Native Init V3089 DOOMGENERIC Remaining Smoothness Audit

## Summary

- Cycle: `V3089`
- Date: `2026-06-23`
- Type: live, non-flash audit on the already-installed V3086 image.
- Resident: `A90 Linux init 0.10.100 (v3086-doomgeneric-pageflip-cadence)`.
- Scope: check for remaining causes of perceived DOOM choppiness after UDP input and 60Hz pageflip cadence were proven.

No boot image was built or flashed in this audit.

## Live State

- Managed serial bridge was running and reachable.
- `version` confirmed the V3086 resident.
- `status` reported `selftest fail=0`, low CPU/GPU utilization, and no system-level thermal or load indication that would explain sustained stutter.
- `video demo doom loop-status` showed no active loop before the bounded timing probe.
- Final `selftest` after the probe still reported `fail=0`.

## DOOM Status Markers

- Frame IPC: `shared-mmap-seq`.
- Presenter pacing: `presenter-pageflip-pace-socket`.
- Present mode/path: `pageflip` / `kms-dumb-buffer-pageflip`.
- Pageflip min submit interval: `0ms`.
- Helper frame cadence marker: `frame_ms=28`.
- Presenter poll interval: `4ms`.
- Dashboard: `minimal-fastdraw`, large 3:2 frame scale, metrics disabled.
- Input: UDP/NCM to `DG_GetKey` with serial doompad fallback.
- Audio: `native-audio-corun-tone-v3053`; this is not real DOOM SFX/music.

## Bounded Timing Probe

Command:

`video demo doom loop 180 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- Frames presented: `180`
- Loop rc: `0`
- Shared-frame reader active; presenter buffer allocations: `1`
- Pace socket active: `1`
- Pace tokens sent: `180`
- Pace socket failures/timeouts: `0` / `0`

Stage timing:

| Stage | Average | Max |
| --- | ---: | ---: |
| alloc | `1us` | `18us` |
| shared-frame read/copy | `179us` | `858us` |
| KMS begin/clear | `4546us` | `4693us` |
| dashboard/draw | `4303us` | `4554us` |
| KMS pageflip/present | `2245us` | `11845us` |
| total | `11273us` | `21648us` |

Pageflip telemetry:

- Flip events: `180`
- Flip delta min/avg/max: `16611us` / `16625us` / `16642us`

Interpretation:

- The display/pageflip cadence itself is stable at the panel vblank cadence.
- Shared-frame IPC is not a bottleneck in this sample.
- CPU scaling/draw cost is measurable, but average total frame work remains below one vblank interval.
- Occasional total-frame maxima remain worth longer histogramming, but they do not look like the dominant sustained choppiness source.

## Source Findings

The DOOM engine uses `TICRATE=35`, so game logic naturally advances in about `28.6ms` ticks. Without interpolation, true DOOM movement/animation will not look like native 60fps motion even when the panel presents at 60Hz.

The current A90 adapter also has a stronger port-specific suspect:

- `DG_GetTicksMs()` returns `fake_ticks_ms`.
- `DG_SleepMs(ms)` only increments that fake counter.
- The V3079+ pace-socket loop removes the outer `usleep(frame_ms)` when presenter pacing is active.
- Therefore helper wall-clock pacing is now driven by pageflip tokens, while the engine's internal clock is driven by the fake sleep path inside the DOOM loop.

This is not the contract expected by doomgeneric, where `DG_GetTicksMs()` should report elapsed milliseconds since launch. The mismatch can produce a valid but non-natural game-time cadence even though KMS pageflip is clean.

## Ranked Remaining Causes

1. **DOOM-native 35Hz game logic with no interpolation.** Some discrete movement is expected and is not a KMS failure.
2. **Adapter fake-time shim versus presenter-paced 60Hz loop.** This is the highest-value port-specific suspect left.
3. **Large 3:2 dashboard scaling/draw cost.** Current draw average is about `4.3ms`; not dominant in the short probe, but still a useful A/B comparison against 1:1/no-dashboard.
4. **Foreground validation log noise.** Foreground timing prints per-frame status; continuous background play suppresses that path, so this mostly affects validation output size.
5. **Real DOOM audio is absent.** Current audio is a bounded native tone co-run; lack of SFX/music is expected behavior, not a runtime failure.
6. **Host NCM setup remains operational.** V3088 proved UDP input after host setup; if input appears dead after USB re-enumeration, run the checked NCM host setup helper before blaming DOOM.

## Recommended Next Unit

Build a source-only candidate that instruments the DOOM engine time path before changing behavior:

- Add helper telemetry for `DG_GetTicksMs`, accumulated `DG_SleepMs`, `I_GetTime`, `gametic`, `presented_frames`, and tick count per presented frame.
- Run a short foreground timing loop and confirm whether game ticks are advancing at 35Hz, 60Hz, or an uneven pattern.
- Then test a monotonic-clock adapter candidate if the fake-time telemetry confirms drift or over-ticking.
- Keep pageflip, shared-frame IPC, UDP input, and dashboard minimal path unchanged while isolating the clock change.
- Separately keep a 1:1/no-dashboard A/B run as the fallback if clock telemetry is clean.

## Safety

- No flash was performed.
- No forbidden partition was touched.
- Runtime changes were limited to read-only status commands and one bounded DOOM foreground timing probe.
- Public report redacts host/device IP, MAC, interface, serial, and storage UUID identifiers.
