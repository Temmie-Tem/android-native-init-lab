# Native Init V3224 GPU H3 MRT Component Mask Source Build

## Summary

- Cycle: `V3224`
- Track: GPU first-triangle H3.6: keep the V3222 shader/SP/raster/VPC path and change the MRT component mask to Mesa's full RT0 mask.
- Decision: `v3224-gpu-h3-mrt-component-mask-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3224_gpu_h3_mrt_component_mask_probe.img`
- Boot SHA256: `035e6918f3404162b79a640d3aeb189a4986a807cc776ad28e10e63a6a2f93b2`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3222_gpu_h3_vpc_linkage_probe.img`
- Init: `A90 Linux init 0.11.39 (v3224-gpu-h3-mrt-component-mask-probe)`

## Included Delta

- Keeps the V3222 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, SP control values, GRAS/RB coverage defaults, and VPC linkage sentinels.
- Changes `GPU_H3_COLOR_OUTPUT_MASK` from `0x1` to `0xf`, which programs `RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE` with Mesa's full RT0 component mask.
- Removes stale preserved-ramdisk DOOM engines before packing V3224 and gates the final boot image at 64MiB to protect the boot partition.
- This tests a bounded FS/MRT/RB output component-mask gap; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3224 builder and focused H3 source test.
- `unittest`: V3224 GPU H3 mrt-component-mask source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3224 identity plus mrt-component-mask H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-mrt-component-mask-probe-candidate`.
