# Native Init V3318 GPU M1 Monitor Dashboard Live

## Summary

- Cycle: `V3318`
- Track: GPU rung 3, M1 on-panel static system-monitor dashboard.
- Candidate: `workspace/private/inputs/boot_images/boot_linux_v3318_gpu_m1_monitor_dashboard.img`
- Candidate SHA256: `e5a3905e94f65d8a8a071955cea92ddd3e0037c0c3839946f9c5c2357fdd6858`
- Init after flash: `A90 Linux init 0.11.89 (v3318-gpu-m1-monitor-dashboard)`
- Result: PASS. The M1 dashboard rendered through the existing KMS/draw primitives, held on-panel for 5 s, and reported
  `present_rc=0` with the M0 sampler-derived CPU, GPU, thermal, and battery telemetry.
- Next: M2 GPU-accelerated live graphs using the 2D textured-quad/blit path.

## Flash Gate

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Local candidate SHA256: `e5a3905e94f65d8a8a071955cea92ddd3e0037c0c3839946f9c5c2357fdd6858`
- Remote staged image SHA256 matched the local candidate.
- Boot block prefix readback SHA256 matched the local candidate.
- Rollback image verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v48.img`
  SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery/TWRP image verified before flash:
  `workspace/private/inputs/firmware/twrp/recovery.img`
  SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`

## Health

- Pre-flash resident: `A90 Linux init 0.11.88 (v3317-gpu-m0-monitor-sampler)`
- Pre-flash `status`: `selftest pass=12 warn=1 fail=0`
- Pre-flash `selftest`: `pass=12 warn=1 fail=0`
- Flash-helper post-boot verification reached V3318 and reported `status` with `selftest pass=12 warn=1 fail=0`.
- The first standalone post-flash command chain hit serial `ATAT` noise and lacked an END marker. Restarting the managed
  bridge restored clean framing; this was a host/bridge framing event, not a device health failure.
- Standalone post-restart health:
  - `version`: `0.11.89`, build `v3318-gpu-m1-monitor-dashboard`
  - `selftest`: `pass=12 warn=1 fail=0`
- Post-probe `selftest`: `pass=12 warn=1 fail=0`

## M1 Probe

Command:

```text
gpu m1-monitor-dashboard-probe --samples 3 --interval-ms 200 --hold-ms 5000
```

Key telemetry:

- `gpu.m1.monitor.scope=static-dashboard-existing-draw-primitives`
- `gpu.m1.monitor.samples_requested=3`
- `gpu.m1.monitor.interval_ms=200`
- `gpu.m1.monitor.hold_ms=5000`
- `gpu.m1.monitor.power_write_attempted=0`
- `gpu.m1.monitor.kgsl_submit_attempted=0`
- `gpu.m1.monitor.kms_present_attempted=1`
- `gpu-m1-monitor-dashboard: presented framebuffer 1080x2400 on crtc=133`
- `gpu.m1.monitor.cpu.count=8`
- `gpu.m1.monitor.cluster.count=3`
- `gpu.m1.monitor.history.count=3`
- `gpu.m1.monitor.gpu.model=Adreno640v2`
- `gpu.m1.monitor.fb.initialized=1`
- `gpu.m1.monitor.fb.width=1080`
- `gpu.m1.monitor.fb.height=2400`
- `gpu.m1.monitor.fb.stride=4352`
- `gpu.m1.monitor.present_rc=0`
- `gpu.m1.monitor.hold_elapsed_ms=5000`
- `gpu.m1.monitor.elapsed_ms=5482`
- `gpu.m1.monitor.result=dashboard-presented`
- `A90P1 END seq=7 cmd=gpu rc=0 errno=0 duration_ms=5482 flags=0x0 status=ok`

## Safety Result

- M1 used read-only `/proc` and `/sys` telemetry plus the existing KMS present path.
- It did not submit KGSL command buffers, did not write any power/display sysfs node, and did not touch backlight, PWM,
  PMIC, regulator, GDSC, GPIO, forbidden partitions, Wi-Fi connect, DHCP, or ping.
- No rollback was needed.

## Conclusion

M1 is closed. The monitor now has an on-panel static dashboard fed by the live-proven M0 sampler and displayed through
the existing native-init draw/KMS path. The next rung is M2: live scrolling graphs via the GPU-accelerated 2D path.
