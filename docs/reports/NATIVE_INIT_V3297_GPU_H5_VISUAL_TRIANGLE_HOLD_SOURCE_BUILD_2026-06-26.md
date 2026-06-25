# Native Init V3297 GPU H5 Visual Triangle Hold Source Build

## Summary

- Cycle: `V3297`
- Track: GPU H5 human visual close after V3296 strict telemetry proof.
- Decision: `v3297-gpu-h5-visual-triangle-hold-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3297_gpu_h5_visual_triangle_hold_probe.img`
- Boot SHA256: `a0728c476f7fa6793d28fc930d7dcdf8c3eac99dc3db44e7044274c5431f4e80`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.74 (v3297-gpu-h5-visual-triangle-hold-probe)`

## Included Delta

- Keeps the V3296 strict GPU proof path: H3 tiled color target, A2D linearization, nonzero/center/corner verifier.
- Presents a recognizable centered triangle by scaling the linear nonzero mask bbox and filling it with a solid high-contrast color.
- Stops autohud before KMS presentation so the proof screen is not immediately overwritten.
- Adds a bounded visual hold with `gpu.h5.vis.result=triangle-presented-held` on success.

## Safety

- KMS present stays on the existing `/dev/dri/card0` path.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, zero-copy scanout, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3297 builder and focused source test.
- `unittest`: V3297 visual source contract plus existing H5 strict source regression coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3297 identity plus H5 visual hold telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h5-visual-triangle-hold-probe-candidate`.
