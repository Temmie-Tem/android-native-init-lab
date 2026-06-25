# Native Init V3218 GPU H3 SP CNTL0 Linkage Source Build

## Summary

- Cycle: `V3218`
- Track: GPU first-triangle H3.3: keep the V3216 hand-encoded `mov.f32f32` VS/FS payloads and add Mesa-derived A6xx SP control bits.
- Decision: `v3218-gpu-h3-sp-cntl0-linkage-shader-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3218_gpu_h3_sp_cntl0_linkage_probe.img`
- Boot SHA256: `f94aabf1476d89612fcc6260b0640948ee7d852c2192039bc451b84f162c4b57`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3216_gpu_h3_minimal_ir3_mov_shader_probe.img`
- Init: `A90 Linux init 0.11.36 (v3218-gpu-h3-sp-cntl0-linkage-probe)`

## Included Delta

- Keeps the V3216 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, and hand-encoded shader payloads.
- VS `SP_VS_CNTL_0` now sets `FULLREGFOOTPRINT=1` plus `MERGEDREGS`, matching the Mesa A6xx geometry-stage control shape for a shader using r0.
- FS `SP_PS_CNTL_0` now sets `FULLREGFOOTPRINT=1`, `INOUTREGOVERLAP`, and `MERGEDREGS`; `THREAD64` remains zero-valued.
- Removes stale preserved-ramdisk DOOM engines before packing V3218 and gates the final boot image at 64MiB to protect the boot partition.
- This removes one concrete H3 no-pixel gap; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3218 builder and focused H3 source test.
- `unittest`: V3218 GPU H3 sp-cntl0-linkage source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3218 identity plus sp-cntl0-linkage H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-sp-cntl0-linkage-probe-candidate`.
