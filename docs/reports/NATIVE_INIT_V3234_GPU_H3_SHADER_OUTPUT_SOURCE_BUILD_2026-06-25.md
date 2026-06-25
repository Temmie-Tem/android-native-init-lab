# Native Init V3234 GPU H3 Shader Output Source Build

## Summary

- Cycle: `V3234`
- Track: GPU first-triangle H3.11: keep the V3232 shader/SP/raster/VPC/MRT/fragment-input/VPC-LM-SIV/static-context path and separate VS/FS output registers from VFD input registers.
- Decision: `v3234-gpu-h3-shader-output-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3234_gpu_h3_shader_output_probe.img`
- Boot SHA256: `d9dc5774c2722272bcc96021ec1c6c82cb9aa25f9010acbc7855b23a0787d0ad`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3232_gpu_h3_static_context_probe.img`
- Init: `A90 Linux init 0.11.44 (v3234-gpu-h3-shader-output-probe)`

## Included Delta

- Keeps the V3232 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, SP CNTL0 values, GRAS/RB coverage defaults, VPC linkage sentinels, VPC LM/SIV state, full RT0 component mask, shader-mode setup, fragment-input defaults, and static-context defaults.
- Changes the hand-assembled shaders so VFD still writes input `r0.xy`, but VS outputs clip position through `r1.xyzw` and FS writes color through `r1.x`; `SP_VS_OUTPUT_REG0` and `SP_PS_OUTPUT_REG0` now point at regid `0x04`.
- Records the Mesa source basis as `fd6_program.cc::emit_vpc()` and `emit_fs_outputs()`, where VS/FS output regids are programmed through SP/VPC maps rather than implicit shader terminator bits.
- Removes stale preserved-ramdisk DOOM engines before packing V3234 and gates the final boot image at 64MiB to protect the boot partition.
- This tests the bounded shader-output/input-register overlap hypothesis; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`emit_shader_regs`, `emit_fs_inputs`, `emit_vpc`).
- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3234 builder and focused H3 source test.
- `unittest`: V3234 GPU H3 shader-output source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3234 identity plus Shader Output H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-shader-output-probe-candidate`.
