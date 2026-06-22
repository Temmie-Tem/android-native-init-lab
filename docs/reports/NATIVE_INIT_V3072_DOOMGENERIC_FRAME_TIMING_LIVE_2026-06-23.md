# Native Init V3072 DOOMGENERIC Frame Timing Live

## Summary

- Cycle: `V3072`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3072-doomgeneric-frame-timing-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3071_doomgeneric_frame_timing.img`
- Boot SHA256: `6c26f341453b505aab85cba76caee6ab1aefe69d702f37d4370baf78da6e5a29`
- Init after flash: `A90 Linux init 0.10.93 (v3071-doomgeneric-frame-timing)`

## Flash Gate

- Built artifact was checksummed before flash.
- Rollback images were present and matched the required SHA256 values for `v2321` and `v2237`; `v48` fallback was present.
- Recovery/TWRP files were present under the private firmware input path.
- Flash path: `native_init_flash.py` only.
- Flash helper verified local marker, remote pushed-image SHA256, boot readback prefix SHA256, reboot to native init, and post-boot `version`/`status`.

## Health

- Pre-flash resident: `0.10.92 (v3069-doomgeneric-metrics-cache)`.
- Pre-flash DOOM loop was stopped before flashing.
- Post-flash health: `selftest pass=12 warn=1 fail=0`.
- Post-flash storage/runtime: SD-backed runtime mounted and writable.
- Post-flash transport: serial ready, NCM/tcpctl ready on the device side.

## DOOM Status Markers

- `video.demo.engine.bridge=v3071-doomgeneric-frame-timing`
- `video.demo.engine.active=doomgeneric-private-link-v3071-frame-timing`
- `video.demo.engine.helper=/bin/a90_doomgeneric_private_engine_v3071`
- `video.demo.doom.loop.frame_ms=28`
- `video.demo.doom.presenter.pacing=helper-frame-mtime`
- `video.demo.doom.presenter.poll_ms=4`
- `video.demo.doom.presenter.reader=reused-loop-buffer`
- `video.demo.doom.presenter.buffer_reuse=1`
- `video.demo.doom.loop.timing_probe=1`
- `video.demo.doom.loop.timing=frame-ipc-kms-stage-us`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.metrics_interval_frames=30`
- `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`
- `video.demo.doom.dashboard.large_frame=0`
- `video.demo.doom.dashboard.frame_scale=1:1`
- `video.demo.input.active=udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- `video.demo.input.udp_port=30570`

## Foreground Timing Probe

Foreground `video demo doom loop 90 --wad runtime-private --sha256 EXPECTED` passed with:

- `frames_presented=88`
- `poll_count=104`
- `helper_done=1`
- `display.rc=0`
- `loop.rc=0`
- `presenter.buffer_allocations=1`

Stage timing, in microseconds:

| Stage | Average | Max |
| --- | ---: | ---: |
| alloc | 1 | 26 |
| frame-file read | 486 | 1065 |
| KMS begin | 3017 | 3128 |
| dashboard/draw | 10127 | 62109 |
| KMS present | 15075 | 15932 |
| total | 28706 | 70129 |

## Interpretation

The raw 1MB frame-file IPC read is not the dominant cost in this run: average read time was below `0.5ms`, and max read time was about `1.1ms`.

The larger steady cost is KMS present, around `15ms`, consistent with display/vblank or DRM atomic commit waiting. The visible stutter candidate is the dashboard/draw stage: average draw was around `10ms`, but the max jumped to about `62ms`, pushing total frame time to about `70ms` on the worst sampled frame. That matches the operator-visible "뚝뚝 끊김" better than the frame-file read path.

The next highest-value rendering candidate is therefore not direct frame-file elimination first. It is to reduce or isolate dashboard draw spikes: make dashboard repaint incremental, throttle slow dashboard metric refresh more aggressively, or temporarily run a pure-DOOM/no-dashboard timing comparison.

## Continuous Functional Check

- Repaired host NCM route with the checked `ncm_host_setup.py setup` helper after reboot re-enumerated the host interface.
- Started continuous loop with `video demo doom loop-start 0 --wad runtime-private --sha256 EXPECTED`.
- Loop status after start: `active=1`, `continuous=1`, presenter PID recorded.
- Frame artifact existed at the V3071 frame path with expected byte size `1024000`.
- Sent compact UDP input packets over USB NCM.
- Device input-state file advanced to `seq=703` and returned to all-up state.
- Loop status after UDP input remained `active=1`, `continuous=1`.

## Pacing And Stack Probe

- Short in-device mtime sampling still showed frame-file updates mostly in `30ms` and `40ms` steps.
- `top` during the continuous loop showed the presenter around `4.5%` CPU and the DOOM engine around `1.8%` CPU, with the system mostly idle.
- Presenter stack sample was again in `drm_atomic_commit` via `drm_mode_setcrtc`, with `wchan=kthread_flush_work`.
- Engine `wchan` was `hrtimer_nanosleep`.

## Operational Notes

- A concurrent serial validation attempt produced lock waiting/no-output; after cancellation, sequential `selftest`, status, loop, UDP, and stack probes all passed. Continue to keep cmdv1 validation sequential.
- The repeated host-side NCM route issue reproduced again after reboot/re-enumeration. Any UDP input test should preflight `ncm_host_setup.py status|setup`.

## Safety

- No forbidden partition was touched.
- No raw host-side partition command was used outside `native_init_flash.py`.
- No Wi-Fi credential action was attempted.
- Public report redacts host/device IP, MAC, interface, UUID, and serial identifiers.
- DOOM loop was left active for operator visual inspection.
