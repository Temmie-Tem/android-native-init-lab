# Native Init V3070 DOOMGENERIC Metrics Cache Live

## Summary

- Cycle: `V3070`
- Track: active Video playback / DOOM capstone frame pacing.
- Decision: `v3070-doomgeneric-metrics-cache-live-pass`
- Result: PASS
- Flashed artifact: `workspace/private/inputs/boot_images/boot_linux_v3069_doomgeneric_metrics_cache.img`
- Boot SHA256: `660bf97fcb43df419c1ecc8eef20a127f2be1bb88180340eb4bc63e107e8acad`
- Init after flash: `A90 Linux init 0.10.92 (v3069-doomgeneric-metrics-cache)`

## Flash Gate

- Built artifact was checksummed before flash.
- Rollback images were present and matched the required SHA256 values for `v2321` and `v2237`; `v48` fallback was present.
- Recovery/TWRP files were present under the private firmware input path.
- Flash path: `native_init_flash.py` only.
- Flash helper verified local marker, remote pushed-image SHA256, boot readback prefix SHA256, reboot to native init, and post-boot `version`/`status`.

## Health

- Pre-flash resident: `0.10.91 (v3067-doomgeneric-reader-reuse)`.
- Pre-flash DOOM loop was stopped before flashing.
- Post-flash health: `selftest pass=12 warn=1 fail=0`.
- Post-flash storage/runtime: SD-backed runtime mounted and writable.
- Post-flash transport: serial ready, NCM/tcpctl ready on the device side.

## DOOM Status Markers

- `video.demo.engine.bridge=v3069-doomgeneric-metrics-cache`
- `video.demo.engine.active=doomgeneric-private-link-v3069-metrics-cache`
- `video.demo.engine.helper=/bin/a90_doomgeneric_private_engine_v3069`
- `video.demo.doom.loop.frame_ms=28`
- `video.demo.doom.presenter.pacing=helper-frame-mtime`
- `video.demo.doom.presenter.poll_ms=4`
- `video.demo.doom.presenter.reader=reused-loop-buffer`
- `video.demo.doom.presenter.buffer_reuse=1`
- `video.demo.doom.dashboard.native=1`
- `video.demo.doom.dashboard.metrics_interval_frames=30`
- `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`
- `video.demo.doom.dashboard.large_frame=0`
- `video.demo.doom.dashboard.frame_scale=1:1`
- `video.demo.input.active=udp-ncm-to-DG_GetKey-with-serial-doompad-fallback`
- `video.demo.input.udp_port=30570`

## Live Functional Check

- Started continuous loop with `video demo doom loop-start 0 --wad runtime-private --sha256 EXPECTED`.
- Loop status after start: `active=1`, `continuous=1`, presenter PID recorded.
- Frame artifact existed at the V3069 frame path with expected byte size `1024000`.
- Repaired host NCM route with the checked `ncm_host_setup.py setup --interface <host-ncm-iface>` helper after reboot re-enumerated the host interface.
- Sent compact UDP input packets over USB NCM.
- Device input-state file advanced to `seq=603` and returned to all-up state.
- Loop status after UDP input remained `active=1`, `continuous=1`.

## Pacing Probe

- Short in-device mtime sampling still showed frame-file updates mostly in `30ms` and `40ms` steps.
- `top` during the continuous loop showed the presenter around `4.0%` CPU and the DOOM engine around `2.0%` CPU, with the system mostly idle.
- CPU saturation and broad thermal throttling remain unlikely as the primary stutter cause.

## Stack Probe

The prior V3068 sample found the presenter blocked in the dashboard thermal path:

- `wsa881x_get_temp`
- `thermal_zone_get_temp`
- `temp_show`
- `sysfs_kf_seq_show`
- `vfs_read`

After V3069 metrics caching, the sampled presenter wait point moved to DRM display commit:

- `kthread_flush_work`
- `msm_atomic_commit`
- `drm_atomic_commit`
- `drm_mode_setcrtc`
- `drm_ioctl`

The engine was sampled in `hrtimer_nanosleep`, which is expected for the paced frame loop. The presenter state sample was sleeping with `wchan=kthread_flush_work`; the engine state sample was sleeping with `wchan=hrtimer_nanosleep`.

## Result

V3069 proves dashboard metric caching is bootable and preserves health, WAD playback, native dashboard visibility, audio corun startup, and UDP input. It removes the previously sampled per-frame thermal/sysfs SoundWire stall from this live sample, but it does not eliminate the visible `30ms`/`40ms` frame-file cadence pattern.

The remaining strongest suspects are now the 1MB raw frame-file IPC path and the DRM atomic mode-set/commit presentation path. A direct/shared KMS buffer path, or at least a lower-copy producer-presenter handoff, is the next structural rendering candidate if the operator still sees stutter.

## Operational Notes

- The repeated host-side NCM route issue reproduced again after reboot/re-enumeration. Any UDP input test should preflight `ncm_host_setup.py status|setup`.
- One long diagnostic `cmdv1x` status command hit a decode/validation mismatch; shorter sequential commands and stack probes passed immediately afterward.

## Safety

- No forbidden partition was touched.
- No raw host-side partition command was used outside `native_init_flash.py`.
- No Wi-Fi credential action was attempted.
- Public report redacts host/device IP, MAC, interface, UUID, and serial identifiers.
- DOOM loop was left active for operator visual inspection.
