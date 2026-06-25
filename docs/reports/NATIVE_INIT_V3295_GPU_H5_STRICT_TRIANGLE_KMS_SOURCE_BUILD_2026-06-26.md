# Native Init V3295 GPU H5 Strict Triangle KMS Source Build

## Summary

- Cycle: `V3295`
- Track: GPU first-triangle H5 strict sample proof after V3294 A2D-linearized KMS telemetry proof.
- Decision: `v3295-gpu-h5-strict-triangle-kms-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3295_gpu_h5_strict_triangle_kms_probe.img`
- Boot SHA256: `f20b4ff3ab76fd0c8d854ede72f13079cf0f90fa248dad059768647fa8a7e4ae`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.73 (v3295-gpu-h5-strict-triangle-kms-probe)`

## Included Delta

- Keeps the V3290/V3292 H3 triangle draw path and its `RGBA8 tile6_3` + flag MRT render target unchanged.
- Keeps the bounded A6xx A2D stage after the H3 draw to copy the tiled/flagged color target into a linear RGBA8 buffer.
- Zero-initializes the linear buffer so the verifier can count true non-zero color instead of sentinel mismatch.
- H5 now requires non-zero linear pixels, a non-zero center sample, and zero exterior corner samples before presenting to `/dev/dri/card0`.
- KMS presentation copies the strict-verified linearized H3 snapshot rather than the raw tile-order buffer.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent reads the linear snapshot over a bounded pipe and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, zero-copy scanout, or forbidden partition work.

## Validation

- `py_compile`: V3295 builder and focused source test.
- `unittest`: V3295 GPU H5 strict sample source contract plus existing H3 source regression coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3295 identity plus H5 strict A2D-linearized KMS telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h5-strict-triangle-kms-probe-candidate`.
