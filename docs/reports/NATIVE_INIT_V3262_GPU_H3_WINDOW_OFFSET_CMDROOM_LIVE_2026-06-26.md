# Native Init V3262 GPU H3 Window Offset Cmdroom Live

## Summary

- Cycle: `V3262`
- Track: GPU H3 first-triangle sysmem-prep ordering before H4 readback proof.
- Decision: `v3262-gpu-h3-window-offset-live-invalid-cmdroom`
- Result: INVALID GPU DATAPOINT
- Device flash: `yes`, through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flashed image: `workspace/private/inputs/boot_images/boot_linux_v3261_gpu_h3_window_offset_probe.img`
- Boot SHA256: `39b19755763a2f68b7e61b90eb114510f82d59e6f99ca0a1b4d91bc42bb2fdf8`
- Init after flash: `A90 Linux init 0.11.57 (v3261-gpu-h3-window-offset-probe)`

## What Was Tested

- Added Mesa sysmem-prep zero window offsets after the direct-render marker and before the visibility packet trio:
  `RB_WINDOW_OFFSET=0`, `RB_RESOLVE_WINDOW_OFFSET=0`, `SP_WINDOW_OFFSET=0`, and `TPL1_WINDOW_OFFSET=0`.
- Expected H3 stream size became `260` dwords with `98` state register writes.
- Firmware materialization was requested with the H3 probe to keep the G0 firmware-class precondition satisfied.

## Live Result

- Flash helper confirmed local SHA, recovery push SHA, boot readback SHA, and native-init version/status.
- Post-flash health passed after a host-side serial bridge framing retry: `selftest pass=12 warn=1 fail=0`.
- H3 telemetry was not a valid GPU no-pixel result because command assembly failed before submit:
  - `gpu.h3.draw.result=returned-error`
  - `gpu.h3.draw.cmd_write_rc=-1`
  - `gpu.h3.draw.pm4_dwords=0`
  - `gpu.h3.draw.state_reg_writes=0`
  - `gpu.h3.draw.submit_rc=-1`
- Root cause: `GPU_G4_CMD_MAX_DWORDS=256` was smaller than the expected `260`-dword H3 stream.
- Post-probe health remained clean: `selftest pass=12 warn=1 fail=0`.

## Conclusion

- V3262 proves only a bounded host-side PM4 assembly guard issue.
- It does not prove or disprove the window-offset hypothesis.
- Corrective unit: V3263 raises the shared command guard to `320` dwords while preserving the same H3 window-offset stream.

## Safety

- Boot partition only, via checked flash helper.
- No forbidden partition writes.
- No PMIC/GDSC/regulator/GPIO write.
- No proprietary blob, full Mesa compiler port, or KMS presentation.
