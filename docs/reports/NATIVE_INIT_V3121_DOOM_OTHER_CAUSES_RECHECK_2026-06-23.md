# Native Init V3121 DOOM Other Causes Recheck

- Date: 2026-06-23
- Cycle: `V3121`
- Track: DOOM visible demo residual stutter/audio/input audit after V3120 source build.
- Decision: `v3121-doom-other-causes-recheck-pass`

## Scope

This was a no-flash, read-only recheck. It audited whether any cause other than
the already identified large CPU scale path and DOOM game-tic cadence remains
credible for the operator-observed "fast input, but stepped/choppy motion" feel.

No boot image was built, flashed, or rebooted.

## Current Device State

- Managed serial bridge: present and connected to the native endpoint.
- Resident: `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`.
- `status`: transport/storage/display ready; `selftest fail=0`.
- `selftest verbose`: `pass=11 warn=1 fail=0`.
- DOOM candidate is not currently resident; V3120 remains a source-built boot
  image awaiting live validation.

Rollback assets were present and matched the pinned gate:

- `v2321` rollback SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- `v2237` fallback SHA256:
  `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- `v48` final fallback exists.
- V3120 candidate SHA256:
  `fb7d561731a0b426f03fc70050a80d57ad33897f3befffd9d22d187d22fbb9e3`

## Evidence Reviewed

### 1:1 Pageflip Path

V3101/V3105/V3106 show that the 1:1 path is not a display infrastructure
bottleneck:

- V3101 300-frame loop: `flip_delta_avg_us=16627`, `flip_delta_max_us=16661`.
- V3101 sequence telemetry: `shared_missed_frames=0`, max sequence gap `1`.
- V3105 paced-tic diagnostic: `flip_delta_avg_us=16626`,
  `flip_delta_max_us=16650`, `shared_missed_frames=0`.
- V3106 recheck: `frames_presented=300`, `duplicate_frame_polls=0`,
  `shared_missed_frames=0`, `pace_socket.failures=0`.

Interpretation: KMS pageflip cadence, shared-frame sequencing, and new-frame
sync are not credible primary causes in the proven 1:1 path.

### DOOM Game-Tic Cadence

V3101 proved the original-speed path presents at panel cadence while DOOM game
state advances at the 35 Hz tic cadence:

- 300 displayed frames, but only `150` changed `gametic` samples.
- `dump_gametic.max_same_run=2`.

V3105 forced one game tic per presenter token and eliminated repeated dump
gametics, but that diagnostic changes gameplay speed and is not a production
fix.

Interpretation: the residual "stepped" feel with otherwise responsive input is
expected for un-interpolated original-speed DOOM on a 60 Hz panel. This is a
quality backlog item, not an infrastructure bug.

### Large Display Path

The original large 3:2 CPU scaler was a real stutter source:

- V3095 reduced draw average from the large 3:2 path's roughly `4.3 ms` to
  roughly `0.8 ms` in 1:1 and removed the recurring 33 ms pageflip gaps.

Hardware plane scaling was audited and then exhausted:

- V3107: DRM exposed compatible planes with src/dst rectangle properties.
- V3109/V3111: live candidates fell back to CPU scaling.
- V3113/V3115: cached CRTC and atomic candidates repeatedly failed the plane
  commit path with `-22` and still fell back to CPU scaling.

The current practical large path is pre-scaled producer output:

- V3117: pre-scaled producer active, but still two-vblank cadence.
- V3119: no-full-clear + pre-scaled producer produced a clean 60 Hz loop:
  `flip_delta_avg_us=16730`, `flip_delta_max_us=33268`,
  `shared_missed_frames=0`, with one expected outlier class but clean
  classification.

Interpretation: large-screen smoothness is no longer blocked by the old
presenter CPU scaler when using the V3119 path, but the direct shared-blit
copy-removal candidate still needs live validation to quantify whether
`timing.read.avg_us` matters.

### Audio

V3106 confirmed that foreground `video demo doom loop ...` does not start the
audio co-run worker. Background `loop-start` starts a bounded native tone worker
successfully, but real DOOM SFX/music is explicitly not implemented:

- `video.demo.doom.audio.real_doom_sfx=0`
- Current sound mode is a native bounded tone co-run, not engine SFX/music.

Interpretation: missing DOOM sound is a separate feature gap, not a visual
stutter cause.

### Serial Management Path

Several live reports record occasional serial command framing issues such as a
missing `A90P1 END` or one retry-needed selftest. Gameplay input no longer
depends on the serial status-poll path in the optimized route, but validation
commands can still need slower/recovered host transport settings.

Interpretation: serial command fragility can affect validation/dashboard
commands, but it is not the current primary gameplay input or visual cadence
cause.

## Ranked Remaining Causes / Issues

1. **Expected DOOM cadence:** original-speed DOOM is 35 Hz game-state update on
   a 60 Hz panel. Without interpolation or a deliberately lower-rate present
   policy, some visible stepping is normal.
2. **V3120 not live-validated:** direct shared blit may reduce read/copy cost,
   but it has not yet been flashed and measured. This is a remaining validation
   gap, not a known blocker.
3. **Large-frame cost budget:** V3119 is clean enough for 60 Hz evidence, but
   large output still has real pixel work. Keep measuring draw/read/present
   before promotion.
4. **Real DOOM audio absent:** the demo can play a bounded tone on `loop-start`,
   but no DOOM SFX/music path exists yet.
5. **Serial command validation fragility:** keep gameplay input separated from
   serial polling and keep serial validation commands retry/slow-mode aware.

## Recommended Next Unit

Proceed with a rollback-gated V3122 live validation of the existing V3120
direct-shared-blit candidate:

- Flash only `boot_linux_v3120_doomgeneric_direct_shared_blit.img`.
- Require marker `video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit`.
- Compare V3122 `timing.read.avg_us`, `timing.draw.avg_us`, pageflip cadence,
  and shared-sequence health against V3119.
- Roll back to `v2321` and verify `selftest fail=0`.

If V3122 shows little or no improvement, the next meaningful work is not more
IPC telemetry; it is either a quality policy for 35 Hz DOOM presentation or the
real DOOM audio/SFX path.
