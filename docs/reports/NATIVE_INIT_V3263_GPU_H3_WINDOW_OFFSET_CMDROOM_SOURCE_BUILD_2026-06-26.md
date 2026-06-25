# Native Init V3263 GPU H3 Window Offset Cmdroom Source Build

## Summary

- Cycle: `V3263`
- Track: GPU H3 first-triangle sysmem-prep ordering before H4 readback proof.
- Decision: `v3263-gpu-h3-window-offset-cmdroom-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3263_gpu_h3_window_offset_cmdroom_probe.img`
- Boot SHA256: `f38f2fdb7cb71cabc6603e606bcd28965715e128f8211bf767f47f851da7f3d8`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3259_gpu_h3_visibility_packets_probe.img`
- Init: `A90 Linux init 0.11.58 (v3263-gpu-h3-window-offset-cmdroom-probe)`

## Included Delta

- Keeps the V3259 shader payload, direct-render marker, visibility packet trio, A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.
- Adds Mesa sysmem-prep zero window offsets immediately after the direct-render marker and before the visibility packet trio: `RB_WINDOW_OFFSET=0`, `RB_RESOLVE_WINDOW_OFFSET=0`, `SP_WINDOW_OFFSET=0`, and `TPL1_WINDOW_OFFSET=0`.
- Raises the shared PM4 command guard from `256` to `320` dwords so the expected `260`-dword H3 stream can be assembled instead of failing at `cmd_write_rc=-1`.
- Expected PM4 size rises from `252` to `260` dwords; expected register writes rise from `94` to `98`.
- Removes the preserved V3259 DOOM engine entry before packing V3263 to keep the boot image under the 64MiB gate.

## Source Basis

- Local Mesa sysmem prep: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc` (`fd6_emit_sysmem_prep`, `set_window_offset`).
- Local Mesa A6xx register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`RB_WINDOW_OFFSET=0x8890`, `RB_RESOLVE_WINDOW_OFFSET=0x88d4`, `SP_WINDOW_OFFSET=0xb4d1`, `TPL1_WINDOW_OFFSET=0xb307`).
- V3260 live result left this sysmem-prep window-offset group as the next concrete Mesa/H3 command-stream mismatch when a full captured diff was not immediately available.
- V3262 live result showed the first V3261 window-offset build exceeded the old `GPU_G4_CMD_MAX_DWORDS=256` guard and failed before submit (`cmd_write_rc=-1`, `pm4_dwords=0`).

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3263 builder and shader audit.
- `unittest`: V3263 GPU H3 window-offset cmdroom source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3263 identity plus window offset and command-room telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-window-offset-cmdroom-probe-candidate`.
