# Native Init V3289 GPU H3 Blend Output State Source Build

## Summary

- Cycle: `V3289`
- Track: GPU H3 first-triangle cffdump-shaped blend/output state probe before H4 readback proof.
- Decision: `v3289-gpu-h3-blend-output-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3289_gpu_h3_blend_output_probe.img`
- Boot SHA256: `10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.70 (v3289-gpu-h3-blend-output-probe)`

## Included Delta

- Keeps the V3288 live-tested VFD/VS contract, A640 magic-block, direct-render, sysmem, RGBA8 tile6_3 flag-MRT, and cffdump bary-FS baseline.
- Sets the remaining direct-sysmem-compatible blend/output registers from the V3286 A640 cffdump diff: `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.
- Leaves cffdump reference `SP_VS_CONST_CONFIG=0x101` deferred because that path requires VS constant-buffer replay; V3289 remains a bounded blend/output-state probe.
- Expected PM4 size stays `335` dwords; state register writes stay `121`; VFD draw-local writes stay `20`.

## Source Basis

- `workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py` identified the blend/output state as the highest-priority remaining direct-sysmem-compatible structural delta after V3288.
- The reference values come from local A640 cffdump draw[2]: `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3289 builder, shader audit, cffdump diff, and focused source tests.
- `unittest`: V3289 GPU H3 blend/output state source contract and shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3289 identity plus blend/output state telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-blend-output-probe-candidate`.
