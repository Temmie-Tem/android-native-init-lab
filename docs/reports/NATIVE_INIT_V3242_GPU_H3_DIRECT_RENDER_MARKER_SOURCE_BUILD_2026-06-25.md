# Native Init V3242 GPU H3 Direct Render Marker Source Build

## Summary

- Cycle: `V3242`
- Track: GPU H3 first-triangle direct-render marker before H4 readback proof.
- Decision: `v3242-gpu-h3-direct-render-marker-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3242_gpu_h3_direct_render_marker_probe.img`
- Boot SHA256: `eb472fa77edfe20cfeeb5dd280279ba1203e2d4e3fd34d236d81e780bcb5ef13`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3232_gpu_h3_static_context_probe.img`
- Init: `A90 Linux init 0.11.48 (v3242-gpu-h3-direct-render-marker-probe)`

## Included Delta

- Adds Mesa/freedreno A6xx `fd6_set_render_mode(...RM6_DIRECT_RENDER)` equivalent to H3: `CP_SET_MARKER` opcode `0x65` payload `0x00000001` immediately after the initial WFI and before H3 3D state.
- Keeps the sysmem RB CCU cache-control state (`RB_CCU_CNTL=0x10000000`) derived from Adreno640v2 / Mesa `GPUId(640)` with `num_ccu=2`, color offset `0x20000`, and depth offset `0`.
- Keeps the V3240 sample-location disable state, V3238 fresh-boot firmware-class materialize prep, and V3236 H3 r1 shader-output/fullregfootprint=2 candidate active.
- Records direct-render marker telemetry with `gpu.h3.draw.render_marker_source=mesa-freedreno-a6xx-fd6-set-render-mode-rm6-direct-render` and `gpu.h3.draw.cp_set_marker=0x%x`.
- Records RB CCU telemetry with `gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2`, `rb_ccu_cntl`, `rb_ccu_color_offset`, and `rb_ccu_depth_offset`.
- Expects H3 state emission to stay at 92 register writes and grow from 231 to 233 PM4 dwords.
- Removes stale preserved-ramdisk DOOM engines before packing V3242 and gates the final boot image at 64MiB to protect the boot partition.
- This tests the missing CP-level direct/sysmem render-mode entry before advancing to H4 interior/exterior readback proof.

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

- `py_compile`: V3242 builder and focused H3 source test.
- `unittest`: V3242 GPU H3 direct-render marker source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3242 identity plus direct-render marker H3 telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-direct-render-marker-probe-candidate`.
