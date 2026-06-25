# Native Init V3284 GPU H3 A640 Magic Block Source Build

## Summary

- Cycle: `V3284`
- Track: GPU H3 first-triangle A640 device-DB non-zero init-magic block probe before H4 readback proof.
- Decision: `v3284-gpu-h3-a640-magic-block-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3284_gpu_h3_a640_magic_block_probe.img`
- Boot SHA256: `7eacd6670856beaeea681d1df6deb3169bcee68fe730c8dcb050b6fdc28b6572`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.68 (v3284-gpu-h3-a640-magic-block-probe)`

## Included Delta

- Keeps the V3280 direct-render/sysmem/varying-IJ/RGBA8/flag-MRT baseline intact.
- Keeps the V3282 `RB_DBG_ECO_CNTL=0x04100000` write and adds the rest of the non-zero A640/a6xx_gen2 device-DB magic block.
- Places the block in the H3 context first-restore/init portion before shader and 3D draw state.
- Raises the shared GPU command-buffer dword guard from `320` to `384` because this block raises expected H3 PM4 size to `329` dwords.
- Expected 3D state register writes remain `121`; init-magic register writes are `9`; VFD draw-local writes remain `14`.

## Source Basis

- Operator-staged `/tmp/a90-mesa-gpu-src/a640_magic_regs.txt` records the A640/a6xx_gen2 non-zero magic register block from Mesa `freedreno_devices.py`.
- This unit does not change `RB_CCU_CNTL`; that value stays the existing computed A640 sysmem CCU value.
- `PC_POWER_CNTL` and `VFD_POWER_CNTL` here are GPU command-stream registers from the Mesa device DB block; this unit does not touch PMIC, GDSC, regulator, GPIO, sysfs power, or forbidden partitions.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3284 builder, shader audit, and focused source contract tests.
- `unittest`: V3284 GPU H3 A640 magic-block source contract and H3 shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3284 identity plus A640 magic-block telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-a640-magic-block-probe-candidate`.
