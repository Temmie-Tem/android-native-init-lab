# Native Init V3310 GPU 2D Bbox Checkerboard Source Build

## Summary

- Cycle: `V3310`
- Track: GPU accelerated 2D D1, bbox-local checkerboard texture sample readback.
- Decision: `v3310-gpu-2d-d1-bbox-checkerboard-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3310_gpu_2d_d1_bbox_checkerboard_probe.img`
- Boot SHA256: `77c26859a449e73abf96bbb66c8087e687ba8cc9301ed9d41c885419008c15f3`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3303_gpu_compute_c3_kms_probe.img`
- Init: `A90 Linux init 0.11.82 (v3310-gpu-2d-d1-bbox-checkerboard-probe)`

## Included Delta

- Adds `gpu d1-texture-checkerboard-probe` to the native GPU command set.
- Uploads a 128x128 linear RGBA8 checkerboard texture plus one sampler descriptor and one TEXMEMOBJ descriptor.
- Uses the V3305 ir3-disasm-verified FD640 textured FS (`sam ... s#0, t#0`) and a clip-space quad.
- Restores the inherited D1 viewport path that V3306/V3307 proved can draw a 64x64 textured region.
- Linearizes the rendered TILE6_3 target and requires all 64 checkerboard samples inside the measured bbox to match.

## Pattern Gate

- Expected texture: 16px checker blocks, RGB `0x303030` and `0xd0d0d0`.
- PASS requires a non-empty `linear_readback_bbox`, `texture_bbox_sample_count=64`, `texture_bbox_sample_match_count=64`, and `texture_bbox_sample_mismatch_count=0`.
- Full 128x128 viewport coverage is parked as a separate geometry/viewport follow-up; this gate proves D1 texture sampling in the known-drawing bbox.
- This source/build report records the gate; the live report must record the device-side readback counts.

## Safety

- KGSL userspace readback only; no KMS present in D1.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3310 builder and focused source test.
- `unittest`: V3310 D1 source contract plus V3304/V3305 coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3310 identity plus D1 texture telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Textured FS SHA256: `4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3`
- D0 reference: `v3304-fd6-texture-reference-recon`
- D1 shader gate: `v3305-verified-textured-fs-shader-bytes`
- Candidate type: `gpu-2d-d1-bbox-checkerboard-probe-candidate`.
