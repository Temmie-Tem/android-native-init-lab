# Native Init V3216 GPU H3 Minimal ir3 Mov Shader Source Build

## Summary

- Cycle: `V3216`
- Track: GPU first-triangle H3.2: replace the terminator-only shader with minimal hand-encoded ir3 `mov.f32f32` VS/FS payloads.
- Decision: `v3216-gpu-h3-minimal-ir3-mov-shader-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3216_gpu_h3_minimal_ir3_mov_shader_probe.img`
- Boot SHA256: `594cb31e298ce21605ae9fe4c01f138d2493daf30917d235230dba375f0e5929`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3214_gpu_h3_ir3_end_terminator_probe.img`
- Init: `A90 Linux init 0.11.35 (v3216-gpu-h3-minimal-ir3-mov-shader-probe)`

## Included Delta

- Keeps the V3214 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, and readback telemetry.
- VS payload uses `mov.f32f32 r0.z, 0.0`, `mov.f32f32 r0.w, 1.0`, then `end`; VFD still supplies `r0.xy` from the 3-vertex buffer.
- FS payload uses `mov.f32f32 r0.x, 1.0`, then `end`, with a single-channel `FMT6_32_FLOAT` MRT/output mask.
- Removes stale preserved-ramdisk DOOM engines before packing V3216 and gates the final boot image at 64MiB to protect the boot partition.
- This is the first bounded shader-color draw attempt after V3214 retirement; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3216 builder and focused H3 source test.
- `unittest`: V3216 GPU H3 minimal-ir3-mov source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3216 identity plus minimal-ir3-mov H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-minimal-ir3-mov-shader-probe-candidate`.
