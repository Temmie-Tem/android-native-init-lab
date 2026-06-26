# Native Init V3318 GPU M1 Monitor Dashboard Source Build

## Summary

- Cycle: `V3318`
- Track: GPU rung 3, M1 on-panel static system-monitor dashboard.
- Decision: `v3318-gpu-m1-monitor-dashboard-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3318_gpu_m1_monitor_dashboard.img`
- Boot SHA256: `e5a3905e94f65d8a8a071955cea92ddd3e0037c0c3839946f9c5c2357fdd6858`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3317_gpu_m0_monitor_sampler.img`
- Init: `A90 Linux init 0.11.89 (v3318-gpu-m1-monitor-dashboard)`

## Included Delta

- Extends `a90_monitor.c/.h` with a static dashboard renderer that reuses the M0 read-only sampler.
- Adds `gpu m1-monitor-dashboard-probe [--samples N] [--interval-ms N] [--hold-ms N]`.
- Discovers CPU IDs dynamically from `/sys/devices/system/cpu`, groups clusters from `cpufreq/related_cpus`, and labels the discovered clusters by max frequency.
- Samples per-core `/proc/stat` deltas, online state, current/min/max CPU frequency, memory, loadavg, KGSL GPU model/busy/frequency/temp, thermal summary, and battery status/capacity/temperature/voltage/current/power.
- Treats optional missing values as `-1`/`?` telemetry instead of failing the probe.

## M1 Gate

- Command: `gpu m1-monitor-dashboard-probe --samples 3 --interval-ms 200 --hold-ms 5000`
- PASS requires `gpu.m1.monitor.result=dashboard-presented`, `present_rc=0`, CPU discovery, history samples, derived cluster labels, KGSL readouts, and thermal/battery readouts.
- This is KMS-present only through the existing display path: no KGSL submit and no power/sysfs writes.

## Safety

- Read-only `/proc` and `/sys` file opens only.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, Wi-Fi connect, DHCP, or ping.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3318 builder and focused source test.
- `unittest`: V3318 M1 source/dispatch/builder contract.
- Compile: focused AArch64 native-init compile with existing baseline warnings only.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3318 identity plus M1 dashboard telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Node enum baseline: `v3316-gpu-m0-system-monitor-node-enum-pass`
- M0 sampler baseline: `v3317-gpu-m0-monitor-sampler-live-pass`
- Candidate type: `gpu-m1-monitor-dashboard-candidate`.
