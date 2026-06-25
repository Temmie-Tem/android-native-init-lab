# Native Init V3293 GPU H5 Linear Triangle KMS Source Build

## Summary

- Cycle: `V3293`
- Track: GPU first-triangle H5 presentation quality after V3292 raw tile-order KMS telemetry proof.
- Decision: `v3293-gpu-h5-linear-triangle-kms-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3293_gpu_h5_linear_triangle_kms_probe.img`
- Boot SHA256: `59b7973d99a7d5a44384d3390ad261231f9fab1b16ee21fce48b9f0537e89e70`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)`

## Included Delta

- Keeps the V3290/V3292 H3 triangle draw path and its `RGBA8 tile6_3` + flag MRT render target unchanged.
- Adds a bounded A6xx A2D stage after the H3 draw to copy the tiled/flagged color target into a new linear RGBA8 buffer.
- H5 now requires the linear buffer to contain changed pixels before presenting to `/dev/dri/card0`.
- KMS presentation copies the linearized H3 snapshot rather than the raw tile-order buffer.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent reads the linear snapshot over a bounded pipe and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, zero-copy scanout, or forbidden partition work.

## Validation

- `py_compile`: V3293 builder and focused source test.
- `unittest`: V3293 GPU H5 linear source contract plus existing H3 source regression coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3293 identity plus H5 A2D-linearized KMS telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h5-linear-triangle-kms-probe-candidate`.
