# Native Init V3103 DOOMGENERIC Gametic Present Live

## Summary

- Cycle: `V3103`
- Artifact under test: `workspace/private/inputs/boot_images/boot_linux_v3102_doomgeneric_gametic_present.img`
- Artifact SHA256: `79c32a132ff69871b84482e432ac6127c717a8fb3764484a863326575e1c91a1`
- Resident after flash: `A90 Linux init 0.10.107 (v3102-doomgeneric-gametic-present)`
- Decision: `v3103-doomgeneric-gametic-present-live-pass-with-cadence-regression`

V3103 flashed the exact V3102 boot artifact and verified resident health. The
changed-gametic-only helper policy did remove repeated `dump_gametic` publications, but
it made the visible cadence worse: the 300-frame helper loop presented only 150 frames,
with pageflip deltas averaging about 49.5 ms. This candidate should not be adopted as the
smoothness fix.

## Flash Gate

- Local boot image Android magic: pass.
- Local and readback SHA256: `79c32a132ff69871b84482e432ac6127c717a8fb3764484a863326575e1c91a1`.
- Rollback precondition: v2321 clean identity image, v2237 fallback, v48 fallback, and TWRP recovery image present.
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Post-flash version/status verification: pass.
- Post-flash selftest retry: `pass=12 warn=1 fail=0`.
- Post-loop selftest: `pass=12 warn=1 fail=0`.

One immediate post-flash selftest attempt lost the `A90P1 END` marker after serial
framing noise. A slower retry returned a complete selftest with `fail=0`, so this was
recorded as a serial framing issue, not a resident health regression.

## DOOM Status

- Active bridge: `v3102-doomgeneric-gametic-present`.
- Engine: `doomgeneric-private-link-v3102-gametic-present`.
- Frame IPC: `shared-mmap-seq`.
- Presenter: `kms-dumb-buffer-pageflip`.
- Pacing: `presenter-pageflip-pace-socket`.
- Scale: `large_frame=0`, `frame_scale=1:1`, `scale_path=raw-rowcopy`.
- Input: `udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`.
- Sequence telemetry: enabled.
- Gametic-present-only mode: enabled.
- Tick pace interval: `14286 us`.
- Metrics dashboard pacing: disabled/minimal.

## Live Results

### 180-frame helper loop

- `frames_presented=89`, `display.rc=0`, `loop.rc=0`, `helper_done=1`.
- `timing.total.avg_us=8474`, `timing.total.max_us=24664`.
- `timing.read.avg_us=187`, `timing.read.max_us=900`.
- `timing.draw.avg_us=810`, `timing.draw.max_us=1406`.
- `timing.present.avg_us=2923`, `timing.present.max_us=19220`.
- `seq.new_frame_polls=89`, `seq.duplicate_frame_polls=566`, `seq.read_errors=57`.
- `seq.shared_missed_frames=0`, `seq.shared_max_sequence_gap_frames=1`.
- `flip_events=89`, `flip_delta_avg_us=49488`, `flip_delta_min_us=16626`, `flip_delta_max_us=49885`.
- `pace_socket.tokens_sent=180`, `pace_socket.idle_tokens_sent=179`, `pace_socket.failures=0`, `pace_socket.wait_timeouts=0`.

Phase telemetry:

- `loop_tick.samples=180`
- `loop_tick.gametic_changed=90`
- `loop_tick.gametic_repeated=90`
- `draw_gametic.samples=222`
- `draw_gametic.changed_transitions=90`
- `draw_gametic.repeated_transitions=131`
- `dump_gametic.samples=90`
- `dump_gametic.changed_transitions=89`
- `dump_gametic.repeated_transitions=0`
- `dump_gametic.max_same_run=1`
- `dump_gametic.emitted_changed_only=90`
- `dump_gametic.skipped_same_gametic=90`

### 300-frame helper loop

- `frames_presented=150`, `display.rc=0`, `loop.rc=0`, `helper_done=1`.
- `timing.total.avg_us=8134`, `timing.total.max_us=24281`.
- `timing.read.avg_us=193`, `timing.read.max_us=2090`.
- `timing.draw.avg_us=815`, `timing.draw.max_us=1419`.
- `timing.present.avg_us=2608`, `timing.present.max_us=16801`.
- `seq.new_frame_polls=150`, `seq.duplicate_frame_polls=974`, `seq.read_errors=72`.
- `seq.shared_missed_frames=0`, `seq.shared_max_sequence_gap_frames=1`.
- `flip_events=150`, `flip_delta_avg_us=49533`, `flip_delta_min_us=16623`, `flip_delta_max_us=49888`.
- `pace_socket.tokens_sent=300`, `pace_socket.idle_tokens_sent=299`, `pace_socket.failures=0`, `pace_socket.wait_timeouts=0`.

Phase telemetry:

- `loop_tick.samples=300`
- `loop_tick.gametic_changed=150`
- `loop_tick.gametic_repeated=150`
- `draw_gametic.samples=342`
- `draw_gametic.changed_transitions=150`
- `draw_gametic.repeated_transitions=191`
- `dump_gametic.samples=150`
- `dump_gametic.changed_transitions=149`
- `dump_gametic.repeated_transitions=0`
- `dump_gametic.max_same_run=1`
- `dump_gametic.emitted_changed_only=150`
- `dump_gametic.skipped_same_gametic=150`

## Interpretation

The experiment answered the immediate suspicion:

- Repeated published frames were real in V3101, and V3102 removed them from the dump path.
- Removing repeated `gametic` frames did not improve smoothness; it reduced visible frame
  delivery to roughly one pageflip every three display refreshes.
- Shared-frame IPC is still not dropping generated frames: `shared_missed_frames=0`.
- KMS/pageflip is still functional: both bounded loops returned `display.rc=0`, `loop.rc=0`,
  and `pace_socket.failures=0`.
- 1:1 row-copy scale is active, so large software scaling is not the current dominant
  cause.

The remaining visual issue is therefore not a hidden dashboard scale or frame IPC bug.
It is the mismatch between DOOM's non-interpolated game-state cadence and the display
cadence, plus this candidate's idle-token scheduling causing changed frames to arrive too
sparsely.

## Other Issues Checked

- Shared-frame read errors increased in changed-only mode (`57-72`), but no shared frames
  were missed. These errors are polls that hit no complete new frame while the presenter is
  intentionally waiting for changed `gametic` output.
- Pageflip deltas are the decisive regression: V3101's 300-frame loop averaged about
  `16627 us`, while V3103 averaged about `49533 us`.
- System health after the loops stayed clean: `status` and `selftest` reported the V3102
  resident with `fail=0`.
- Audio remains a separate issue. `video demo doom status` reports
  `native-audio-corun-tone-v3053`, but `audio status` is read-only, `native_play_gate=closed`,
  and `audio_playback_attempted=0`. If the demo has no audible sound, handle that as a
  playback activation/route validation unit, not as part of the visual cadence path.

## Next Step

Do not promote V3102 as the demo baseline. The next bounded visual candidates should be:

1. Revert to the V3100/V3101 60 Hz presentation baseline for demo usability.
2. Test a true single-pacer model where the helper owns a stable tick cadence and the
   presenter only displays the latest complete frame, instead of sending idle tick tokens
   from the presenter poll loop.
3. If the goal is visibly smoother-than-original DOOM motion, evaluate interpolation or a
   deliberate non-original simulation timing mode as a separate, explicitly semantic
   change.
