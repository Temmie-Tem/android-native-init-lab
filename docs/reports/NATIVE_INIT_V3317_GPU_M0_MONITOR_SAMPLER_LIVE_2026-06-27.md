# Native Init V3317 GPU M0 Monitor Sampler Live

## Summary

- Cycle: `V3317`
- Track: GPU rung 3, M0 on-panel system-monitor data layer.
- Candidate: `workspace/private/inputs/boot_images/boot_linux_v3317_gpu_m0_monitor_sampler.img`
- Candidate SHA256: `47dcc28d9a9de86a56258bfd066839d5d3e3c93f9c5b55e6de266d3ffb5ba813`
- Init after flash: `A90 Linux init 0.11.88 (v3317-gpu-m0-monitor-sampler)`
- Result: PASS. The read-only M0 sampler and history ring ran on-device and reported derived SD855 clusters, per-core
  CPU usage/frequency, memory/load, KGSL GPU, thermal, and battery telemetry.
- Next: M1 static dashboard rendering with existing draw primitives.

## Flash Gate

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Local candidate SHA256: `47dcc28d9a9de86a56258bfd066839d5d3e3c93f9c5b55e6de266d3ffb5ba813`
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

- Pre-flash resident: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`
- Pre-flash `status`: `selftest pass=12 warn=1 fail=0`
- Pre-flash `selftest verbose`: `pass=12 warn=1 fail=0`
- Flash-helper post-boot verification reached V3317 and reported `status` with `selftest pass=12 warn=1 fail=0`.
- The first standalone post-flash `selftest verbose` attempt after the helper hit serial `ATAT` noise and lacked an END
  marker. Restarting the managed bridge restored clean framing; this was a host/bridge framing event, not a device health
  failure.
- Standalone post-restart health:
  - `version`: `0.11.88`, build `v3317-gpu-m0-monitor-sampler`
  - `status`: `selftest pass=12 warn=1 fail=0`
  - `selftest verbose`: `pass=12 warn=1 fail=0`
- Post-probe `selftest verbose`: `pass=12 warn=1 fail=0`

## M0 Probe

Command:

```text
gpu m0-monitor-sampler-probe --samples 3 --interval-ms 200
```

Key telemetry:

- `gpu.m0.monitor.scope=read-only-sysfs-proc-sampler`
- `gpu.m0.monitor.power_write_attempted=0`
- `gpu.m0.monitor.kms_present_attempted=0`
- `gpu.m0.monitor.cpu.count=8`
- `gpu.m0.monitor.cpu.capacity_readable_count=8`
- `gpu.m0.monitor.cluster.count=3`
- `gpu.m0.monitor.cluster.detect_source=cpufreq-related-cpus-plus-max-freq`
- `gpu.m0.monitor.gpu.model=Adreno640v2`
- `gpu.m0.monitor.history.capacity=16`
- `gpu.m0.monitor.history.count=3`
- `gpu.m0.monitor.cluster.0.label=Silver`
- `gpu.m0.monitor.cluster.0.cpus=0-3`
- `gpu.m0.monitor.cluster.0.min_khz=300000`
- `gpu.m0.monitor.cluster.0.max_khz=1785600`
- `gpu.m0.monitor.cluster.1.label=Gold`
- `gpu.m0.monitor.cluster.1.cpus=4-6`
- `gpu.m0.monitor.cluster.1.min_khz=710400`
- `gpu.m0.monitor.cluster.1.max_khz=2419200`
- `gpu.m0.monitor.cluster.2.label=Prime`
- `gpu.m0.monitor.cluster.2.cpus=7`
- `gpu.m0.monitor.cluster.2.min_khz=825600`
- `gpu.m0.monitor.cluster.2.max_khz=2841600`
- Per-core capacity values were readable: Silver `378`, Gold `871`, Prime `1024`.
- `gpu.m0.monitor.mem.total_kb=5504936`
- `gpu.m0.monitor.mem.available_kb=5201396`
- `gpu.m0.monitor.gpu.busy_pct=0`
- `gpu.m0.monitor.gpu.cur_hz=257000000`
- `gpu.m0.monitor.gpu.max_hz=585000000`
- `gpu.m0.monitor.gpu.temp_millic=42800`
- `gpu.m0.monitor.thermal.zones=79`
- `gpu.m0.monitor.thermal.readable=67`
- `gpu.m0.monitor.thermal.cooling_devices=21`
- `gpu.m0.monitor.thermal.max_type=lmh-dcvs-01`
- `gpu.m0.monitor.thermal.max_millic=75000`
- `gpu.m0.monitor.power.supplies=10`
- `gpu.m0.monitor.power.batteries=1`
- `gpu.m0.monitor.power.chargers=3`
- `gpu.m0.monitor.battery.status=Full`
- `gpu.m0.monitor.battery.capacity_pct=100`
- `gpu.m0.monitor.battery.temp_decic=356`
- `gpu.m0.monitor.battery.voltage_uv=4321000`
- `gpu.m0.monitor.elapsed_ms=479`
- `gpu.m0.monitor.result=sampler-pass`
- `A90P1 END seq=10 cmd=gpu rc=0 errno=0 duration_ms=479 flags=0x0 status=ok`

## Safety Result

- M0 probe was data-layer only.
- It did not open KGSL for submit, did not present through KMS, and did not write any sysfs/proc/power/display node.
- Wi-Fi connect/DHCP/ping were not run.
- No rollback was needed.

## Conclusion

M0 is closed. The system monitor now has a live-proven read-only sampler, dynamically derived Prime/Gold/Silver cluster
labels, per-core usage/frequency, and history ring telemetry. The next rung is M1: render a static dashboard using the
existing draw primitives before moving to GPU-accelerated live graphs in M2.
