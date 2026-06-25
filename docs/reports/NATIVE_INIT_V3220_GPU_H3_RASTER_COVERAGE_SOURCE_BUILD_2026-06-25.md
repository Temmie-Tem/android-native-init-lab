# Native Init V3220 GPU H3 Raster Coverage Source Build

## Summary

- Cycle: `V3220`
- Track: GPU first-triangle H3.4: keep the V3218 shader/SP-control path and add Mesa-derived GRAS raster coverage defaults.
- Decision: `v3220-gpu-h3-raster-coverage-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3220_gpu_h3_raster_coverage_probe.img`
- Boot SHA256: `0ef76e157d47ed5e71f756b5b7bef540300e9bcf3f8d70817a078e70460e594e`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3218_gpu_h3_sp_cntl0_linkage_probe.img`
- Init: `A90 Linux init 0.11.37 (v3220-gpu-h3-raster-coverage-probe)`

## Included Delta

- Keeps the V3218 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, and SP control values.
- Adds `GRAS_SC_RAS_MSAA_CNTL=0`, `GRAS_SC_DEST_MSAA_CNTL=0x4`, and `GRAS_SC_SCREEN_SCISSOR_CNTL=0` so GRAS raster coverage matches the RB non-MSAA target state.
- Removes stale preserved-ramdisk DOOM engines before packing V3220 and gates the final boot image at 64MiB to protect the boot partition.
- This tests a bounded raster/coverage state gap; H4 still requires live readback interior/exterior proof.

## Source Basis

- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.
- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.
- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.
- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.
- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3220 builder and focused H3 source test.
- `unittest`: V3220 GPU H3 raster-coverage source contract.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3220 identity plus raster-coverage H3 markers.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-raster-coverage-probe-candidate`.
