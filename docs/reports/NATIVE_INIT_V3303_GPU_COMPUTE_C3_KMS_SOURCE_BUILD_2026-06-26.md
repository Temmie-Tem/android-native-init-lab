# Native Init V3303 GPU Compute C3 KMS Source Build

## Summary

- Cycle: `V3303`
- Track: GPU compute demo C3, C2 compute-output snapshot presented through KMS.
- Decision: `v3303-gpu-compute-c3-kms-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3303_gpu_compute_c3_kms_probe.img`
- Boot SHA256: `0a041e834cedae3b54bea5c1b4fb70b4be133156e8c9317d8f6c30b304c01e20`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`

## Included Delta

- Extends the C2 compute probe to write a bounded 64KiB UAV snapshot after readback.
- Adds `gpu c3-compute-kms-probe`, which runs C2, verifies the snapshot, expands it to a KMS dumb framebuffer, presents, and holds.
- Keeps the compute proof on the Mesa-style `SP_CS_*`, `LOAD_STATE6`, `RM6_COMPUTE`, and `CP_EXEC_CS` sequence inherited from C2.
- Verifies the 16384-word 128x128 UAV readback contract before KMS presentation.

## Safety

- KGSL userspace plus KMS present only; no panel re-init or power-domain write.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3303 builder and focused source test.
- `unittest`: V3303 C3 source contract plus C2 shader-byte coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3303 identity plus C3 KMS visual telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Shader SHA256: `9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1`
- ASM SHA256: `1f7f223c66a97975e416dce96b0a960933b7fa21b7bf4c6d380b3eb63e31b0d6`
- Candidate type: `gpu-compute-c3-kms-probe-candidate`.
