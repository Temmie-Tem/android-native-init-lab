# Native Init V3287 GPU H3 VFD/VS Contract Source Build

## Summary

- Cycle: `V3287`
- Track: GPU H3 first-triangle cffdump-shaped VFD/VS contract probe before H4 readback proof.
- Decision: `v3287-gpu-h3-vfd-vs-contract-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3287_gpu_h3_vfd_vs_contract_probe.img`
- Boot SHA256: `560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)`

## Included Delta

- Keeps the V3284/V3285 A640 magic-block, direct-render, sysmem, RGBA8 tile6_3 flag-MRT, and cffdump bary-FS baseline.
- Replaces H3's single 2-float vertex fetch with the V3286 cffdump-shaped VFD contract: three fetch/decode streams, 36-byte stride, `VFD_CNTL_0=0x303`, and `VFD_CNTL_1=0xfcfcfc09` (`REGID4VTX=r2.y`).
- Uses vertex payload layout `r0.xyzw` varying color, `r1.xyzw` clip-space position, and `r2.x` sint attribute.
- Changes the hand-assembled VS to a constant-free `r1.xyzw -> r2.xyzw` pass-through while preserving `r0` for the existing cffdump bary FS.
- Leaves cffdump reference `SP_VS_CONST_CONFIG=0x101` deferred because that path requires VS constant-buffer replay; V3287 remains a bounded VFD/VS input-contract probe.
- Expected PM4 size is `335` dwords; state register writes stay `121`; VFD draw-local writes become `20`.

## Source Basis

- `workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py` identified the VFD/VS input contract as the highest-priority remaining structural delta.
- The reference values come from local A640 cffdump draw[2]: `VFD_CNTL_0=0x303`, `VFD_CNTL_1=0xfcfcfc09`, fetch instrs `0xc8200000/0xc8200200/0x44c00400`, dest cntls `0xf/0x4f/0x81`, and stride `36`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3287 builder, shader audit, cffdump diff, and focused source tests.
- `unittest`: V3287 GPU H3 VFD/VS contract source contract and shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3287 identity plus VFD/VS contract telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-vfd-vs-contract-probe-candidate`.
