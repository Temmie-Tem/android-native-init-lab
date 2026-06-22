# Native Init V3101 DOOMGENERIC Phase Telemetry Live

## Summary

- Cycle: `V3101`
- Artifact under test: `workspace/private/inputs/boot_images/boot_linux_v3100_doomgeneric_phase_telemetry.img`
- Artifact SHA256: `e79b748621ef6003a36ce36cf13297741a593e6da07fdf500472f409328f57fa`
- Resident after flash: `A90 Linux init 0.10.106 (v3100-doomgeneric-phase-telemetry)`
- Decision: `v3101-doomgeneric-phase-telemetry-live-pass`

V3101 flashed the exact V3100 boot artifact, verified resident health, and split the
DOOM path into loop tick, real draw, and shared-frame dump telemetry. The dominant
remaining visual stutter source is not KMS pageflip, shared-frame IPC, or scaling. It is
that the engine currently presents at display cadence while the DOOM game state advances
at the 35 Hz tic cadence, so many visible frames repeat the same `gametic`.

## Flash Gate

- Local boot image Android magic: pass.
- Local and readback SHA256: `e79b748621ef6003a36ce36cf13297741a593e6da07fdf500472f409328f57fa`.
- Rollback precondition: v2321 clean identity image, v2237 fallback, v48 fallback, and TWRP recovery image present.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Post-flash version/status verification: pass.
- Post-flash selftest retry: `pass=12 warn=1 fail=0`.
- Post-loop selftest: `pass=12 warn=1 fail=0`.

One immediate post-flash selftest attempt lost the `A90P1 END` marker after serial
framing noise. A slower retry returned a complete selftest with `fail=0`, so this was
recorded as a serial framing issue, not a device health regression.

## DOOM Status

- Active bridge: `v3100-doomgeneric-phase-telemetry`.
- Engine: `doomgeneric-private-link-v3100-phase-telemetry`.
- Frame IPC: `shared-mmap-seq`.
- Presenter: `kms-dumb-buffer-pageflip`.
- Pacing: `presenter-pageflip-pace-socket`.
- Scale: `large_frame=0`, `frame_scale=1:1`, `scale_path=raw-rowcopy`.
- Input: `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`.
- Sequence telemetry: enabled.
- Metrics dashboard pacing: disabled/minimal.

## Live Results

### 180-frame loop

- `frames_presented=180`, `display.rc=0`, `loop.rc=0`, `helper_done=1`.
- `timing.total.avg_us=11230`, `timing.total.max_us=20852`.
- `timing.read.avg_us=180`, `timing.read.max_us=941`.
- `timing.draw.avg_us=787`, `timing.draw.max_us=1376`.
- `timing.present.avg_us=5788`, `timing.present.max_us=13963`.
- `seq.new_frame_polls=180`, `seq.duplicate_frame_polls=2`, `seq.read_errors=12`.
- `seq.shared_missed_frames=0`, `seq.shared_max_sequence_gap_frames=1`.
- `flip_events=180`, `flip_delta_avg_us=16717`, `flip_delta_min_us=16603`, `flip_delta_max_us=33250`.
- `pace_socket.tokens_sent=180`, `pace_socket.failures=0`, `pace_socket.wait_timeouts=0`.

Phase telemetry:

- `loop_tick.samples=180`
- `loop_tick.gametic_changed=90`
- `loop_tick.gametic_repeated=90`
- `loop_tick.draw_changed_iterations=180`
- `draw_gametic.samples=222`
- `draw_gametic.changed_transitions=90`
- `draw_gametic.repeated_transitions=131`
- `dump_gametic.samples=180`
- `dump_gametic.changed_transitions=89`
- `dump_gametic.repeated_transitions=90`
- `dump_gametic.max_same_run=2`

### 300-frame loop

- `frames_presented=300`, `display.rc=0`, `loop.rc=0`, `helper_done=1`.
- `timing.total.avg_us=11043`, `timing.total.max_us=16109`.
- `timing.read.avg_us=181`, `timing.read.max_us=819`.
- `timing.draw.avg_us=782`, `timing.draw.max_us=1358`.
- `timing.present.avg_us=5614`, `timing.present.max_us=9957`.
- `seq.new_frame_polls=300`, `seq.duplicate_frame_polls=0`, `seq.read_errors=11`.
- `seq.shared_missed_frames=0`, `seq.shared_max_sequence_gap_frames=1`.
- `flip_events=300`, `flip_delta_avg_us=16627`, `flip_delta_min_us=16606`, `flip_delta_max_us=16661`.
- `pace_socket.tokens_sent=300`, `pace_socket.failures=0`, `pace_socket.wait_timeouts=0`.

Phase telemetry:

- `loop_tick.samples=300`
- `loop_tick.gametic_changed=150`
- `loop_tick.gametic_repeated=150`
- `loop_tick.draw_changed_iterations=300`
- `draw_gametic.samples=342`
- `draw_gametic.changed_transitions=150`
- `draw_gametic.repeated_transitions=191`
- `dump_gametic.samples=300`
- `dump_gametic.changed_transitions=149`
- `dump_gametic.repeated_transitions=150`
- `dump_gametic.max_same_run=2`

## Interpretation

The display path is now mostly stable:

- 300-frame pageflip timing is essentially one display refresh per frame.
- Shared-frame sequence telemetry saw no missed frames.
- Presenter timing stays below one 16.6 ms frame on the 300-frame loop.
- The 1:1 row-copy path confirms the previous large software scale path is not active.

The visible stutter source is the game-state cadence:

- Every loop iteration changed the draw counter, but only half changed `gametic`.
- The 300-frame loop presented 300 frames but only 150 loop ticks changed game state.
- The dump path also repeats each `gametic` for about two visible frames.
- This matches DOOM's `TICRATE=35` model with a 60 Hz display and no interpolation.

The source confirms the model:

- `I_GetTime()` converts elapsed milliseconds to `TICRATE` units.
- `TryRunTics()` runs game tics from that 35 Hz time base.
- `doomgeneric_Tick()` calls `TryRunTics()` and then `D_Display()`.

This means the remaining "뚝뚝" feel is expected from the current adapter policy:
display frames are smooth, but game-state motion is quantized to the DOOM tic rate.

## Other Issues Checked

- Shared-frame read errors: `11-12` per run, but `shared_missed_frames=0`. The stats
  count a read error when a poll catches an incomplete or invalid shared-frame read; the
  sequence counters show no dropped rendered frames in these runs.
- Pageflip outlier: the 180-frame loop saw one `33250 us` delta, effectively one missed
  vblank. The 300-frame loop did not reproduce it (`max=16661 us`), so it is not the
  dominant cause but should stay on the watch list.
- Serial health check: one selftest command lost framing after flash, then the same
  command passed with slower input. This is a serial command transport wart, not a
  resident health failure.
- Audio: `audio status` is read-only clean for firmware/sound device presence, but
  native playback is still gated (`native_play_gate=closed`) and no audio playback
  attempt was recorded. If the demo has no audible sound, handle it as a separate audio
  route/playback activation issue, not as part of the visual cadence path.
- V3100 telemetry wart: the telemetry file prints `dump_gametic.samples` twice. Values
  are identical and harmless for this run, but the duplicate print should be cleaned in
  the next source-only cleanup or next cadence candidate.

## Next Step

The next visual candidate should avoid trying to make the 35 Hz simulation look like a
60 Hz simulation without interpolation. The bounded options are:

1. Present only when `gametic` changes, yielding a truthful 35 Hz output with fewer
   repeated frames.
2. Keep 60 Hz pageflip but add a lightweight interpolation/prediction layer for player
   view movement. This is more invasive and touches game/render semantics.
3. Try a 35 Hz-aligned presenter cadence first, because it is smaller, reversible, and
   should immediately show whether the perceived stutter is just duplicate-frame cadence.

V3102 should implement option 1 as an additive cadence candidate, with V3100/V3101 kept
as the diagnostic baseline.
