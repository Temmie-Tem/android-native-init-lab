# Native Init V3255 GPU H3 Sysmem Bin-Control Source Build

## Summary

- Cycle: `V3255`
- Track: GPU H3 first-triangle sysmem visibility before H4 readback proof.
- Decision: `v3255-gpu-h3-sysmem-bin-control-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3255_gpu_h3_sysmem_bin_control_probe.img`
- Boot SHA256: `0ccb33c25dcbbf9a8274d2d569c135a48a9ef208bb27e512d0cd73687a651501`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3253_gpu_h3_sp_update_cntl_probe.img`
- Init: `A90 Linux init 0.11.54 (v3255-gpu-h3-sysmem-bin-control-probe)`

## Included Delta

- Keeps the V3253 Mesa-reference shader payload, direct-render marker, RB_CCU sysmem value, pre-draw cache invalidation, and draw-local `SP_UPDATE_CNTL=0x0000009f`.
- Adds Mesa A6xx sysmem render-pass bin controls: `GRAS_SC_BIN_CNTL=0x02c00000` and `RB_CNTL=0x02c00000`.
- Treats `RB_CCU_CNTL=0x10000000` as source-verified for A640 sysmem mode rather than changing it blindly.
- Removes the preserved V3253 DOOM engine entry before packing V3255 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`GRAS_SC_BIN_CNTL`, `RB_CNTL`, `BUFFERS_IN_SYSMEM`, `LRZ_FEEDBACK_EARLY_Z_LATE_Z`).
- Local Mesa sysmem prep: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc` (`fd6_emit_sysmem_prep`, `set_bin_size`).
- Local Mesa A640 device info: `/tmp/a90-mesa-h3-sparse/src/freedreno/common/freedreno_devices.py` (`GPUId(640)`, `num_ccu=2`, `has_lrz_feedback=True`).
- Local Mesa reference trace: `dEQP-VK.draw.indirect_draw.indexed.indirect_draw_count.triangle_list.log` confirms A640 sysmem `RB_CCU_CNTL=0x10000000`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3255 builder and shader audit.
- `unittest`: V3255 GPU H3 sysmem bin-control source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3255 identity plus sysmem bin-control telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-sysmem-bin-control-probe-candidate`.
