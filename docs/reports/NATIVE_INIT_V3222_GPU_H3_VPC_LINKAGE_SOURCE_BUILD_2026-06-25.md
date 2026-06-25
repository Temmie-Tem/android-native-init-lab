# Native Init V3222 GPU H3 VPC Linkage Source Build

## Summary

- Cycle: `V3222`
- Track: GPU first-triangle H3.5: keep the V3220 shader/SP/raster path and add Mesa-derived VPC position/clip-cull linkage sentinels.
- Decision: `v3222-gpu-h3-vpc-linkage-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3222_gpu_h3_vpc_linkage_probe.img`
- Boot SHA256: `f8db5278b0c520f18675ebde42d4f5cd63b35911936624475c0fc7e80d84da39`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3220_gpu_h3_raster_coverage_probe.img`
- Init: `A90 Linux init 0.11.38 (v3222-gpu-h3-vpc-linkage-probe)`

## Included Delta

- Keeps the V3220 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, SP control values, and GRAS/RB coverage defaults.
- Changes `VPC_VS_CNTL` from stride-only `0x00000004` to `0x00ff0004` so absent point-size is explicitly `0xff`, matching Mesa's VPC linkage convention.
- Adds `VPC_VS_CLIP_CULL_CNTL=0x00ffff00`, `VPC_VS_CLIP_CULL_CNTL_V2=0x00ffff00`, and `GRAS_CL_VS_CLIP_CULL_DISTANCE=0` to make the no-clip/no-cull path explicit.
- Removes stale preserved-ramdisk DOOM engines before packing V3222 and gates the final boot image at 64MiB to protect the boot partition.
- This tests a bounded VPC position/clip-cull linkage state gap; H4 still requires live readback interior/exterior proof.

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

- `py_compile`: V3222 builder and focused H3 source test.
- `unittest`: V3222 GPU H3 vpc-linkage source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3222 identity plus vpc-linkage H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-vpc-linkage-probe-candidate`.
