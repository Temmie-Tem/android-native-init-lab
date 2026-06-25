# Native Init V3247 GPU H3 RB_RENDER_CNTL Source Build

## Summary

- Cycle: `V3247`
- Track: GPU H3 first-triangle RB_RENDER_CNTL linkage before H4 readback proof.
- Decision: `v3247-gpu-h3-rb-render-cntl-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3247_gpu_h3_rb_render_cntl_probe.img`
- Boot SHA256: `56ea2b9aa2b46e2c5257db52c4c05a392871bed67fbd6c6a61807a880d3a5f4e`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3244_gpu_h3_r0_output_probe.img`
- Init: `A90 Linux init 0.11.50 (v3247-gpu-h3-rb-render-cntl-probe)`

## Included Delta

- Uses V3244 r0-output image as the preserved-ramdisk base and keeps the V3246 verified hand-assembled ir3 bytes unchanged.
- Keeps the direct-render marker state: `CP_SET_MARKER` opcode `0x65` payload `0x00000001` immediately after the initial WFI and before H3 3D state.
- Keeps the sysmem RB CCU cache-control state (`RB_CCU_CNTL=0x10000000`) derived from Adreno640v2 / Mesa `GPUId(640)` with `num_ccu=2`, color offset `0x20000`, and depth offset `0`.
- Keeps the V3240 sample-location disable state, V3238 fresh-boot firmware-class materialize prep, and V3236 fullregfootprint=2 shader mode active.
- Sets `RB_RENDER_CNTL=0x00000010`, matching Mesa A6xx `fd6_gmem.cc::update_render_cntl()` with `CCUSINGLECACHELINESIZE=2`.
- Keeps VS/PS output regids at `0x00`, so telemetry should still show `sp_vs_output_reg0=0x00000f00`.
- Expects H3 state emission to stay at 92 register writes and 233 PM4 dwords because this changes one existing register value.
- Removes stale preserved-ramdisk DOOM engines before packing V3247 and gates the final boot image at 64MiB to protect the boot partition.
- This isolates whether the no-pixel result is caused by the missing Mesa RB render-control CCU cacheline field before advancing to H4 interior/exterior readback proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- A6xx PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml` (`CP_SET_MARKER`, `RM6_DIRECT_RENDER=1`).
- Mesa/freedreno A6xx render-mode helper: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.h` (`fd6_set_render_mode`).
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`emit_shader_regs`, `emit_fs_inputs`, `emit_vpc`).
- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- Mesa/freedreno GMEM/CCU cache sizing helper: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/fd6_gmem_cache.h`.
- Mesa/freedreno Adreno device table: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3247 builder and focused H3 source test.
- `unittest`: V3247 GPU H3 RB render cntl source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3247 identity plus RB render cntl H3 telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-rb-render-cntl-probe-candidate`.
