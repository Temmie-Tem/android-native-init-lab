# Native Init V3212 GPU H3 Draw Envelope Source Build

## Summary

- Cycle: `V3212`
- Track: GPU first-triangle H3: bind one vertex buffer, emit direct non-indexed `CP_DRAW_INDX_OFFSET`, and summarize offscreen readback.
- Decision: `v3212-gpu-h3-draw-envelope-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3212_gpu_h3_draw_envelope_probe.img`
- Boot SHA256: `a2c7e223b30d361716363e2b8a37b45cecce41b50a35690c2265d0aa6499b938`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3210_gpu_h2_3d_state_probe.img`
- Init: `A90 Linux init 0.11.33 (v3212-gpu-h3-draw-envelope-probe)`

## Included Delta

- Adds `gpu h3-draw-envelope-probe` after the V3210 H2 fixed-function 3D state retire probe.
- Allocates command, color, event, placeholder VS/FS shader, and 3-vertex buffer GPU objects in a child-only KGSL envelope.
- Emits H1 shader-state setup, H2 3D state, A6xx VFD vertex buffer/fetch/dest state, then `CP_DRAW_INDX_OFFSET` for one triangle list of 3 vertices.
- Performs `PC_CCU_FLUSH_COLOR_TS`, waits on the KGSL timestamp, syncs the color buffer back, and reports changed pixel count without presenting to KMS.
- Shader payload is still an explicit zero placeholder. This rung is a bounded draw-envelope probe, not a completed shaded triangle proof.

## Source Basis

- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.
- A6xx VFD register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3212 builder and focused H3 source test.
- `unittest`: V3212 GPU H3 source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3212 identity plus H3 draw-envelope markers.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-draw-envelope-probe-candidate`.
