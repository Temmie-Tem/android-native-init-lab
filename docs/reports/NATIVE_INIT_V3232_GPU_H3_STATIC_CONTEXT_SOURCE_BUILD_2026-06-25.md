# Native Init V3232 GPU H3 Static Context Source Build

## Summary

- Cycle: `V3232`
- Track: GPU first-triangle H3.10: keep the V3230 shader/SP/raster/VPC/MRT/fragment-input/VPC-LM-SIV path and add a Mesa static-context state group.
- Decision: `v3232-gpu-h3-static-context-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3232_gpu_h3_static_context_probe.img`
- Boot SHA256: `08392c39698d52df7794fca1f36f9e2ce14d4fa88e27ad2cae2f644e84dae02d`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3230_gpu_h3_vpc_lm_siv_probe.img`
- Init: `A90 Linux init 0.11.43 (v3232-gpu-h3-static-context-probe)`

## Included Delta

- Keeps the V3230 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, SP CNTL0 values, GRAS/RB coverage defaults, VPC linkage sentinels, VPC LM/SIV state, full RT0 component mask, shader-mode setup, and fragment-input defaults.
- Adds a bounded Mesa `fd6_emit_static_context_regs()` group that was still absent from the hand-built packet: `GRAS_SU_CONSERVATIVE_RAS_CNTL=0`, `VPC_UNKNOWN_9210=0`, `VPC_SO_OVERRIDE=1`, `VPC_RAST_STREAM_CNTL=0`, `PC_STEREO_RENDERING_CNTL=0`, `TPL1_PS_SWIZZLE_CNTL=0`, and `SP_REG_PROG_ID_3=0x0000fcfc`.
- Removes stale preserved-ramdisk DOOM engines before packing V3232 and gates the final boot image at 64MiB to protect the boot partition.
- This tests a bounded missing static-context state gap; H4 still requires live readback interior/exterior proof.

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

- `py_compile`: V3232 builder and focused H3 source test.
- `unittest`: V3232 GPU H3 static-context source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3232 identity plus Static Context H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-static-context-probe-candidate`.
