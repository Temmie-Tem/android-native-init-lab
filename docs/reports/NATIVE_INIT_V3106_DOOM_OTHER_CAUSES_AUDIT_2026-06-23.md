# Native Init V3106 DOOM Other Causes Audit

- Date: 2026-06-23
- Cycle: `V3106`
- Track: DOOM visible demo issue triage after V3105 paced-tic diagnosis.
- Decision: `v3106-doom-other-causes-audit-pass`

## Scope

This was a no-flash audit on the installed V3104/V3105 diagnostic resident. It
checked whether any non-cadence issue still explains the operator-observed
DOOM stutter or missing audio.

No boot image was built or flashed.

## Resident And Health

- Resident: `A90 Linux init 0.10.108 (v3104-doomgeneric-paced-tic)`.
- `status`: resident booted, display ready, transport ready, storage ready.
- `selftest`: `pass=12 warn=1 fail=0`.
- Bridge: managed bridge connected to the native serial endpoint.

## Foreground Loop Recheck

Command shape:

`video demo doom loop 300 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- `frames_presented=300`
- `helper_done=1`
- `display.rc=0`
- `loop.rc=0`
- `timing.total.avg_us=11203`
- `timing.total.max_us=11288`
- `timing.read.avg_us=179`
- `timing.read.max_us=985`
- `timing.draw.avg_us=773`
- `timing.draw.max_us=1122`
- `timing.present.avg_us=5751`
- `timing.present.max_us=5953`
- `seq.new_frame_polls=300`
- `seq.duplicate_frame_polls=0`
- `seq.read_errors=11`
- `seq.shared_missed_frames=0`
- `flip_events=300`
- `flip_delta_min_us=16609`
- `flip_delta_avg_us=16626`
- `flip_delta_max_us=16649`
- `pace_socket.tokens_sent=300`
- `pace_socket.failures=0`
- `pace_socket.wait_timeouts=0`

Interpretation:

- KMS/pageflip cadence is still stable at the expected 60 Hz panel cadence.
- The foreground 1:1 path stays below the 16.6 ms vblank budget.
- `read_errors=11` means the presenter observed no new shared frame during a
  poll, not that it dropped a displayed frame. `shared_missed_frames=0` and
  `duplicate_frame_polls=0` rule it out as the stutter source in this path.

## Audio Finding

The foreground `video demo doom loop ...` path does not start the audio co-run
worker. The audio co-run start is wired to the background
`video demo doom loop-start ...` path.

Observed background start:

`video demo doom loop-start 120 --wad runtime-private --sha256 <expected-runtime-wad-sha256>`

Result:

- `video.demo.doom.audio.corun=1`
- `video.demo.doom.audio.source=native-bounded-tone`
- `video.demo.doom.audio.real_doom_sfx=0`
- `audio.play.worker.started=1`
- `video.demo.doom.audio.start.rc=0`
- `video.demo.doom.loop_start.audio_rc=0`
- `video.demo.doom.loop_start.rc=0`

Worker status/log after completion:

- `audio.play.worker.done=1 rc=0`
- `audio.play.worker.frames_done=480000`
- `audio.play.worker.bytes_done=1920000`
- `audio.play.execute.open.rc=0 errno=0`
- `audio.play.execute.hw_params.rc=0 errno=0`
- `audio.play.execute.sw_params.rc=0 errno=0`
- `audio.play.execute.prepare.rc=0 errno=0`
- `audio.play.execute.drain.rc=0 errno=0`
- `audio.play.execute.done=1`
- `audio.play.integrated.done=1 rc=0`

Interpretation:

- If the operator tested foreground `loop`, no sound is expected from that path.
- `loop-start` does start and complete the bounded native tone worker.
- This is still not real DOOM SFX/music. The current engine path explicitly
  reports `real_doom_sfx=0`; DOOM audio remains a separate implementation task.

## Large Display Path

The active V3104 resident uses the 1:1 path:

- `large_frame=0`
- `frame_scale=1:1`
- `scale_path=raw-rowcopy`

Source inspection shows the large path is still a CPU software scaler:

- 3:2 optimized row-copy fast path: `video_demo_doom_blit_raw_frame_scaled_3_to_2`
- generic nearest fallback: `video_demo_doom_blit_raw_frame_scaled`
- no `drmModeSetPlane` / hardware-plane scaling implementation is present in
  the native-init display path.

Interpretation:

- The remaining large-screen problem is not the 1:1 pageflip/IPC path.
- Large display smoothness still depends on replacing or bypassing the CPU
  per-frame scaler.

## Conclusion

No new visual infrastructure blocker was found in the current 1:1 path. The
remaining issues are:

1. DOOM-inherent 35 Hz game-state cadence on a 60 Hz panel when preserving
   original speed and not interpolating.
2. Large-frame mode still uses CPU software scaling and can exceed the smooth
   demo budget.
3. Foreground `loop` does not start audio; background `loop-start` does.
4. Current DOOM audio is a bounded native tone co-run only, not real DOOM
   SFX/music.

Recommended next unit: implement the scale-path unit already selected in
`GOAL.md`: first audit/try hardware display-plane scaling, then fall back to a
pre-scaled producer or cheaper integer/write-combining CPU blit if plane scaling
is unavailable.
