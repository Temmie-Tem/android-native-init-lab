# Native Init V3268 GPU H3 Raster Mode Source Build

## Summary

- Cycle: `V3268`
- Track: GPU H3 first-triangle polygon raster-mode before H4 readback proof.
- Decision: `v3268-gpu-h3-raster-mode-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Boot SHA256: `8fc356e60545ad36e412367d40b4da6f6f9a9766c6251369684f187c49323240`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3265_gpu_h3_cp_set_mode_probe.img`
- Init: `A90 Linux init 0.11.60 (v3268-gpu-h3-raster-mode-probe)`

## Included Delta

- Keeps the V3265 shader payload, direct-render marker, visibility packet trio, zero window offsets, CP_SET_MODE(0), A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.
- Adds Mesa A6xx rasterizer polygon-mode state for triangles: `VPC_RAST_CNTL=0x3` and `PC_DGEN_RAST_CNTL=0x3`.
- Expected PM4 size rises from `262` to `266` dwords; expected register writes rise from `98` to `100`.
- Removes the preserved V3265 DOOM engine entry before packing V3268 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa Gallium rasterizer: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_rasterizer.cc` emits `VPC_RAST_CNTL(POLYMODE6_TRIANGLES)` and `PC_DGEN_RAST_CNTL(POLYMODE6_TRIANGLES)` for A6xx fill-mode triangles.
- Local Mesa A6xx XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` maps `VPC_RAST_CNTL=0x9108` and `PC_DGEN_RAST_CNTL=0x9981` on A6xx.
- V3267 built a working `cffdump` path and decoded Mesa's included A640 triangle-list `.rd` reference; the draw-state summary also shows both registers at value `0x3` for triangle rasterization.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3268 builder and shader audit.
- `unittest`: V3268 GPU H3 raster-mode source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3268 identity plus raster-mode telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-raster-mode-probe-candidate`.
