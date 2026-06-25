# Native Init V3244 GPU H3 R0 Output Source Build

## Summary

- Cycle: `V3244`
- Track: GPU H3 first-triangle r0 output contract before H4 readback proof.
- Decision: `v3244-gpu-h3-r0-output-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3244_gpu_h3_r0_output_probe.img`
- Boot SHA256: `9764d950f93ada582b5b853c17dcf480635df0aeffe5ee90d6cab7845533c66d`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3242_gpu_h3_direct_render_marker_probe.img`
- Init: `A90 Linux init 0.11.49 (v3244-gpu-h3-r0-output-probe)`

## Included Delta

- Keeps V3242 direct-render marker state: `CP_SET_MARKER` opcode `0x65` payload `0x00000001` immediately after the initial WFI and before H3 3D state.
- Keeps the sysmem RB CCU cache-control state (`RB_CCU_CNTL=0x10000000`) derived from Adreno640v2 / Mesa `GPUId(640)` with `num_ccu=2`, color offset `0x20000`, and depth offset `0`.
- Keeps the V3240 sample-location disable state, V3238 fresh-boot firmware-class materialize prep, and V3236 fullregfootprint=2 shader mode active.
- Changes the H3 hand-assembled ir3 payload to an r0-output fallback: VS passes through `r0.xy` and writes `r0.zw=0/1`; FS writes color to `r0.x`.
- Changes VS/PS output regids from `0x04` to `0x00`, so telemetry should show `sp_vs_output_reg0=0x00000f00`.
- Expects H3 state emission to stay at 92 register writes and 233 PM4 dwords.
- Removes stale preserved-ramdisk DOOM engines before packing V3244 and gates the final boot image at 64MiB to protect the boot partition.
- This isolates whether the no-pixel result is caused by the previous r1 output register contract before advancing to H4 interior/exterior readback proof.

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

- `py_compile`: V3244 builder and focused H3 source test.
- `unittest`: V3244 GPU H3 r0 output source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3244 identity plus r0 output H3 telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-r0-output-probe-candidate`.
