# Native Init V3228 GPU H3 Fragment Input Source Build

## Summary

- Cycle: `V3228`
- Track: GPU first-triangle H3.8: keep the V3226 shader/SP/raster/VPC/MRT path and add Mesa's fragment-input defaults.
- Decision: `v3228-gpu-h3-fragment-input-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3228_gpu_h3_fragment_input_probe.img`
- Boot SHA256: `33d813c9736c912bf692818f7d0936ee90437d750261af959a6b92b606eea9ee`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3226_gpu_h3_shader_mode_probe.img`
- Init: `A90 Linux init 0.11.41 (v3228-gpu-h3-fragment-input-probe)`

## Included Delta

- Keeps the V3226 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, SP CNTL0 values, GRAS/RB coverage defaults, VPC linkage sentinels, full RT0 component mask, and shader-mode setup.
- Adds Mesa-derived fragment input defaults for a no-varying/no-fragcoord/no-sample fragment shader: `GRAS_CL_INTERP_CNTL=0`, `RB_INTERP_CNTL=0`, `RB_PS_INPUT_CNTL=0`, `RB_PS_SAMPLEFREQ_CNTL=0`, `GRAS_LRZ_PS_INPUT_CNTL=0`, and `GRAS_LRZ_PS_SAMPLEFREQ_CNTL=0` from `fd6_program.cc::emit_fs_inputs()`.
- Removes stale preserved-ramdisk DOOM engines before packing V3228 and gates the final boot image at 64MiB to protect the boot partition.
- This tests a bounded fragment input/raster state gap; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`emit_shader_regs`, `emit_fs_inputs`).
- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3228 builder and focused H3 source test.
- `unittest`: V3228 GPU H3 fragment-input source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3228 identity plus fragment-input H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-fragment-input-probe-candidate`.
