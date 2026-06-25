# Native Init V3253 GPU H3 SP_UPDATE_CNTL Source Build

## Summary

- Cycle: `V3253`
- Track: GPU H3 first-triangle draw-state bootstrap before H4 readback proof.
- Decision: `v3253-gpu-h3-sp-update-cntl-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3253_gpu_h3_sp_update_cntl_probe.img`
- Boot SHA256: `1395721839c41ac07ff41379fabaa298d40479b237384add1bcfb6c1837d5769`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3251_gpu_h3_compiler_vs_instrlen_probe.img`
- Init: `A90 Linux init 0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)`

## Included Delta

- Keeps the V3251 Mesa-reference minimal VS, audited FS, shader `instrlen=1`, direct-render marker, RB_RENDER_CNTL, RB_CCU sysmem, and pre-draw cache invalidation state.
- Adds Mesa A6xx draw-state bootstrap register `SP_UPDATE_CNTL=0x0000009f` before H3 shader state, matching the local freedreno draw/program state object pattern.
- Removes the preserved V3251 DOOM engine entry before packing V3253 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`SP_UPDATE_CNTL`, offset `0xbb08`).
- Local Mesa draw emit: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc` (`SP_UPDATE_CNTL=0x000fffff` restore path).
- Local Mesa program state: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`SP_UPDATE_CNTL` before shader/program state).
- Local Mesa reference trace: `dEQP-VK.draw.indirect_draw.indexed.indirect_draw_count.triangle_list.log` draw-local `SP_UPDATE_CNTL=0x0000009f`.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3253 builder and shader audit.
- `unittest`: V3253 GPU H3 SP_UPDATE_CNTL source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3253 identity plus SP_UPDATE_CNTL telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-sp-update-cntl-probe-candidate`.
