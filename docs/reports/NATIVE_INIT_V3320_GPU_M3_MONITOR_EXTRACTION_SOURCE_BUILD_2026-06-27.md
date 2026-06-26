# Native Init V3320 GPU M3 Monitor Extraction Source Build

## Summary

- Cycle: `V3320`
- Track: GPU rung 3, M3 shared GPU monitor extraction.
- Decision: `v3320-gpu-m3-monitor-extraction-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3320_gpu_m3_monitor_extraction.img`
- Boot SHA256: `dd2f4fa31b81340ad35477cb0d23655b9b837887272a4224926311e04ef43ea2`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3319_gpu_m2_monitor_live_graphs.img`
- Init: `A90 Linux init 0.11.91 (v3320-gpu-m3-monitor-extraction)`

## Included Delta

- Extracts the D3-named 2D present path into `gpu_2d_present_*` helpers for BO mapping, GPU sync, submit/wait, linear readback, and KMS copy.
- Routes both `gpu d3-video-texture-present-probe` and `gpu m2-monitor-live-graph-probe` through `gpu_2d_present_create_session` plus `gpu_2d_present_render_frame_to_kms`.
- Adds `gpu m3-monitor-extraction-probe [--frames N] [--interval-ms N] [--timeout-ms N] [--hold-ms N] [--materialize-devnode]` as the shared-layer proof command; it delegates to the M2 live graph path and emits M3 extraction telemetry.

## M3 Gate

- Command: `gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 5000 --materialize-devnode`
- PASS requires `gpu.m3.extract.result=shared-2d-present-monitor-pass`, `gpu.m3.extract.layer=gpu_2d_present_v1`, M2 delegate live graph pass, 12 presented frames, semantic match count 64, `present_rc=0`, focused D3 Bad Apple regression, and `selftest fail=0` after the probe.
- The user visually confirmed the D3 Bad Apple path as visible with normal-looking frames before this extraction unit.
- This is a real KGSL submit path (`kgsl_submit_attempted=1`) plus KMS present, with no power/sysfs writes.

## Safety

- Monitor telemetry sources are read-only `/proc` and `/sys` reads.
- Live KGSL validation may use the existing G0 firmware-cache/devnode materialization path; no power/display sysfs write is part of M3.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, Wi-Fi connect, DHCP, or ping.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3320 builder and focused source test.
- `unittest`: V3320 M3 source/dispatch/builder contract.
- Compile: focused AArch64 native-init compile with existing baseline warnings only.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3320 identity plus M3 extraction telemetry, M2 delegate telemetry, and shared 2D present labels.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Node enum baseline: `v3316-gpu-m0-system-monitor-node-enum-pass`
- M0 sampler baseline: `v3317-gpu-m0-monitor-sampler-live-pass`
- M1 dashboard baseline: `v3318-gpu-m1-monitor-dashboard-live-pass`
- M2 live graph baseline: `v3319-gpu-m2-monitor-live-graphs-live-pass`
- Candidate type: `gpu-m3-monitor-extraction-candidate`.
