# Native Init V3291 GPU H5 Triangle KMS Source Build

## Summary

- Cycle: `V3291`
- Track: GPU first-triangle H5 presentation after V3290 H4 readback proof.
- Decision: `v3291-gpu-h5-triangle-kms-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3291_gpu_h5_triangle_kms_probe.img`
- Boot SHA256: `eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.71 (v3291-gpu-h5-triangle-kms-probe)`

## Included Delta

- Adds `gpu h5-triangle-kms-probe` / `gpu triangle-kms-probe`.
- Reuses the V3290-proven H3 draw/readback path, but H5 mode asks the KGSL child to return a 128x128 color-buffer snapshot before cleanup.
- Keeps KMS ownership in the parent init process, then scales the raw H3 readback into the existing `/dev/dri/card0` dumb framebuffer and presents with `SETCRTC`.
- Marks the first pass as raw tile-order visualization because the H3 target is still `RGBA8 tile6_3`; zero-copy, scaled-plane, blob, and power writes are not attempted.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent reads the snapshot over a bounded pipe and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, zero-copy scanout, or forbidden partition work.

## Validation

- `py_compile`: V3291 builder and focused source test.
- `unittest`: V3291 GPU H5 source contract plus existing H3 source regression coverage.
- Legacy V3204 G5 source test was inspected separately; it is stale against the current shared G4 event helper count and was not used as a V3291 pass criterion.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3291 identity plus H5 KMS telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h5-triangle-kms-probe-candidate`.
