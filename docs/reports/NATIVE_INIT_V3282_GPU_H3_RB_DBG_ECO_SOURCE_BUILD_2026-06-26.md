# Native Init V3282 GPU H3 RB_DBG_ECO Source Build

## Summary

- Cycle: `V3282`
- Track: GPU H3 first-triangle A640 device-DB RB_DBG_ECO init-magic probe before H4 readback proof.
- Decision: `v3282-gpu-h3-rb-dbg-eco-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3282_gpu_h3_rb_dbg_eco_probe.img`
- Boot SHA256: `f2afd2eda2b8632fff582e79c3defe5b9520ecb63d36e0498f3fced945fa9879`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.67 (v3282-gpu-h3-rb-dbg-eco-probe)`

## Included Delta

- Keeps the V3280 direct-render/sysmem/varying-IJ/RGBA8/flag-MRT baseline intact.
- Adds only `RB_DBG_ECO_CNTL=0x04100000` at register `0x8e04` from the A640/a6xx_gen2 freedreno device DB magic block.
- Places the write in the H3 context first-restore/init portion before shader and 3D draw state.
- Defers the rest of the non-zero A640 magic block to the next bounded probe.
- Expected PM4 size is `313` dwords; 3D state register writes remain `121`; init-magic register writes are `1`; VFD draw-local writes remain `14`.

## Source Basis

- Operator-staged `/tmp/a90-mesa-gpu-src/a640_magic_regs.txt` records A640 `RB_DBG_ECO_CNTL off=0x8e04 val=0x04100000` from Mesa `freedreno_devices.py`.
- This unit does not change `RB_CCU_CNTL`; that value stays the existing computed A640 sysmem CCU value.
- This unit does not emit SP/TPL1/VPC/RBP/PC/VFD/UCHE magic values; probe order is RB_DBG_ECO first.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3282 builder, shader audit, and focused source contract tests.
- `unittest`: V3282 GPU H3 RB_DBG_ECO source contract and H3 shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3282 identity plus RB_DBG_ECO telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-rb-dbg-eco-probe-candidate`.
