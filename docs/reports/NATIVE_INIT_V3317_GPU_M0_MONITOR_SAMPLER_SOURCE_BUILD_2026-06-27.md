# Native Init V3317 GPU M0 Monitor Sampler Source Build

## Summary

- Cycle: `V3317`
- Track: GPU rung 3, M0 on-panel system-monitor data layer.
- Decision: `v3317-gpu-m0-monitor-sampler-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3317_gpu_m0_monitor_sampler.img`
- Boot SHA256: `47dcc28d9a9de86a56258bfd066839d5d3e3c93f9c5b55e6de266d3ffb5ba813`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3315_gpu_2d_d3_video_semantic_edge_tolerance.img`
- Init: `A90 Linux init 0.11.88 (v3317-gpu-m0-monitor-sampler)`

## Included Delta

- Adds `a90_monitor.c/.h` with a read-only M0 sampler and fixed-size history ring.
- Adds `gpu m0-monitor-sampler-probe [--samples N] [--interval-ms N]`.
- Discovers CPU IDs dynamically from `/sys/devices/system/cpu`, groups clusters from `cpufreq/related_cpus`, and labels the discovered clusters by max frequency.
- Samples per-core `/proc/stat` deltas, online state, current/min/max CPU frequency, memory, loadavg, KGSL GPU model/busy/frequency/temp, thermal summary, and battery status/capacity/temperature/voltage/current/power.
- Treats optional missing values as `-1`/`?` telemetry instead of failing the probe.

## M0 Gate

- Command: `gpu m0-monitor-sampler-probe --samples 3 --interval-ms 200`
- PASS requires `gpu.m0.monitor.result=sampler-pass`, CPU discovery, history samples, derived cluster labels, KGSL readouts, and thermal/battery readouts.
- This is data-layer only: no KMS present, no GPU submit, and no power/sysfs writes.

## Safety

- Read-only `/proc` and `/sys` file opens only.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, Wi-Fi connect, DHCP, or ping.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3317 builder and focused source test.
- `unittest`: V3317 M0 source/dispatch/builder contract.
- Compile: focused AArch64 native-init compile with existing baseline warnings only.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3317 identity plus M0 sampler telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Node enum baseline: `v3316-gpu-m0-system-monitor-node-enum-pass`
- Candidate type: `gpu-m0-monitor-sampler-candidate`.
