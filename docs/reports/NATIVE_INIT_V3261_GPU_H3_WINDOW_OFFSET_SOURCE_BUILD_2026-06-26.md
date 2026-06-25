# Native Init V3261 GPU H3 Window Offset Source Build

## Summary

- Cycle: `V3261`
- Track: GPU H3 first-triangle sysmem-prep ordering before H4 readback proof.
- Decision: `v3261-gpu-h3-window-offset-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3261_gpu_h3_window_offset_probe.img`
- Boot SHA256: `39b19755763a2f68b7e61b90eb114510f82d59e6f99ca0a1b4d91bc42bb2fdf8`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3259_gpu_h3_visibility_packets_probe.img`
- Init: `A90 Linux init 0.11.57 (v3261-gpu-h3-window-offset-probe)`

## Included Delta

- Keeps the V3259 shader payload, direct-render marker, visibility packet trio, A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.
- Adds Mesa sysmem-prep zero window offsets immediately after the direct-render marker and before the visibility packet trio: `RB_WINDOW_OFFSET=0`, `RB_RESOLVE_WINDOW_OFFSET=0`, `SP_WINDOW_OFFSET=0`, and `TPL1_WINDOW_OFFSET=0`.
- Expected PM4 size rises from `252` to `260` dwords; expected register writes rise from `94` to `98`.
- Removes the preserved V3259 DOOM engine entry before packing V3261 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa sysmem prep: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc` (`fd6_emit_sysmem_prep`, `set_window_offset`).
- Local Mesa A6xx register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`RB_WINDOW_OFFSET=0x8890`, `RB_RESOLVE_WINDOW_OFFSET=0x88d4`, `SP_WINDOW_OFFSET=0xb4d1`, `TPL1_WINDOW_OFFSET=0xb307`).
- V3260 live result left this sysmem-prep window-offset group as the next concrete Mesa/H3 command-stream mismatch when a full captured diff was not immediately available.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3261 builder and shader audit.
- `unittest`: V3261 GPU H3 window-offset source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3261 identity plus window offset telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-window-offset-probe-candidate`.
