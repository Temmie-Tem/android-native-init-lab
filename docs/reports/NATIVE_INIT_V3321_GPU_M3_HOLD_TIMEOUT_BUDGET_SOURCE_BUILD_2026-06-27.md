# Native Init V3321 GPU M3 Hold Timeout Budget Source Build

## Summary

- Cycle: `V3321`
- Track: GPU rung 3, M3 visual hold timeout-budget fix.
- Decision: `v3321-gpu-m3-hold-timeout-budget-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3321_gpu_m3_hold_timeout_budget.img`
- Boot SHA256: `48050046e743694d6e74ed6123b49f87d5d2dd0f87a44bd14e3d548431ca9a49`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3320_gpu_m3_monitor_extraction.img`
- Init: `A90 Linux init 0.11.92 (v3321-gpu-m3-hold-timeout-budget)`

## Included Delta

- Keeps the V3320 `gpu_2d_present_v1` extraction intact.
- Splits the M2/M3 monitor parent watchdog into render timeout plus visual hold budget plus a 5 s margin.
- Adds `gpu.m2.graph.parent_timeout_ms` and `gpu.m2.graph.timeout_split=render-plus-visual-hold` telemetry so a 60 s visual hold no longer races the 60 s render timeout.

## M3 Hold Gate

- Command: `gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 60000 --materialize-devnode`
- PASS requires `gpu.m3.extract.result=shared-2d-present-monitor-pass`, `gpu.m3.extract.layer=gpu_2d_present_v1`, M2 delegate live graph pass, `parent_timeout_ms=125000`, 12 presented frames, semantic match count 64, `present_rc=0`, no timeout for a 60 s hold, and `selftest fail=0` after the probe.
- The user visually confirmed the D3 Bad Apple path as visible with normal-looking frames before the V3320 extraction unit.
- This is a real KGSL submit path (`kgsl_submit_attempted=1`) plus KMS present, with no power/sysfs writes.

## Safety

- Monitor telemetry sources are read-only `/proc` and `/sys` reads.
- Live KGSL validation may use the existing G0 firmware-cache/devnode materialization path; no power/display sysfs write is part of M3.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, Wi-Fi connect, DHCP, or ping.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3321 builder and focused source test.
- `unittest`: V3321 M3 source/dispatch/builder contract.
- Compile: focused AArch64 native-init compile with existing baseline warnings only.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3321 identity plus M3 extraction telemetry, M2 delegate telemetry, timeout split telemetry, and shared 2D present labels.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Node enum baseline: `v3316-gpu-m0-system-monitor-node-enum-pass`
- M0 sampler baseline: `v3317-gpu-m0-monitor-sampler-live-pass`
- M1 dashboard baseline: `v3318-gpu-m1-monitor-dashboard-live-pass`
- M2 live graph baseline: `v3319-gpu-m2-monitor-live-graphs-live-pass`
- M3 extraction baseline: `v3320-gpu-m3-monitor-extraction-telemetry-pass`
- Candidate type: `gpu-m3-hold-timeout-budget-candidate`.
