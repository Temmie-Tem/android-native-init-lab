# Native Init V3251 GPU H3 Compiler VS/Instrlen Source Build

## Summary

- Cycle: `V3251`
- Track: GPU H3 first-triangle shader-load contract before H4 readback proof.
- Decision: `v3251-gpu-h3-compiler-vs-instrlen-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3251_gpu_h3_compiler_vs_instrlen_probe.img`
- Boot SHA256: `ac608fe5914a834b5f895c79ee28b4c4d5212b8fbdbcec0e73408fde92226426`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3249_gpu_h3_cache_invalidate_probe.img`
- Init: `A90 Linux init 0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)`

## Included Delta

- Keeps the V3249 direct-render, RB_RENDER_CNTL, RB_CCU sysmem, and pre-draw cache invalidate state.
- Replaces the H3 VS payload with the repeated Mesa A6xx reference minimal VS bytes: `mov.u32u32 r0.z, 0x3f800000`; `mov.u32u32 r0.w, 0x3f800000`; `end`; zero NOP padding.
- Leaves the V3246 ir3-disasm-audited FS constant-color payload in place.
- Changes H3 shader state to use Mesa-style `instrlen=1` for `SP_VS_INSTR_SIZE`, `SP_PS_INSTR_SIZE`, and CP_LOAD_STATE6 shader units while keeping the copied shader BO payload 128-byte aligned.
- Removes the V3249 preserved DOOM engine before packing V3251 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa reference trace: `/tmp/a90-mesa-h3-sparse/src/freedreno/tests/reference/crash_prefetch.log`.
- Mesa ir3 size logic: `src/freedreno/ir3/ir3.c` (`ir3_collect_info`).
- Mesa A6xx shader state: `src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- Mesa ir3 disassembler: `src/freedreno/isa/ir3-disasm.c`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3251 builder and shader audit.
- `unittest`: V3251 GPU H3 compiler VS/instrlen source contract and updated shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3251 identity plus shader-load contract telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-compiler-vs-instrlen-probe-candidate`.
