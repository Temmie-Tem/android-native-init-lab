# Native Init V3265 GPU H3 CP_SET_MODE Source Build

## Summary

- Cycle: `V3265`
- Track: GPU H3 first-triangle draw-state bootstrap before H4 readback proof.
- Decision: `v3265-gpu-h3-cp-set-mode-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3265_gpu_h3_cp_set_mode_probe.img`
- Boot SHA256: `cb8c579aa4cc694de363d7e2334c202f255431bba9e4f1a385fe0f2b3094ba84`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3263_gpu_h3_window_offset_cmdroom_probe.img`
- Init: `A90 Linux init 0.11.59 (v3265-gpu-h3-cp-set-mode-probe)`

## Included Delta

- Keeps the V3263 shader payload, direct-render marker, visibility packet trio, zero window offsets, A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.
- Adds Mesa restore-path `CP_SET_MODE(0)` immediately after pre-draw CCU/cache invalidation and before H3 shader/state/draw packets.
- Expected PM4 size rises from `260` to `262` dwords; expected register writes remain `98`.
- Removes the preserved V3263 DOOM engine entry before packing V3265 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa restore path: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc` (`fd6_emit_restore` emits `CP_SET_MODE=0`).
- Local Mesa PM4 XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/adreno_pm4.xml` (`CP_SET_MODE=0x63`, A6xx+).
- V3264 live result removed zero window offsets and command-buffer room as primary no-pixel causes, leaving draw-state bootstrap / `CP_SET_MODE` as a concrete Mesa/H3 packet mismatch when a real `.rd` capture is not immediately available.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3265 builder and shader audit.
- `unittest`: V3265 GPU H3 CP_SET_MODE source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3265 identity plus CP_SET_MODE telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-cp-set-mode-probe-candidate`.
