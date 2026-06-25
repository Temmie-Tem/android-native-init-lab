# Native Init V3266 GPU H3 CP_SET_MODE Live

## Summary

- Cycle: `V3266`
- Track: GPU H3 first-triangle draw-state bootstrap before H4 readback proof.
- Decision: `v3266-gpu-h3-cp-set-mode-live-no-pixel`
- Result: NO PIXEL
- Device flash: `yes`, through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flashed image: `workspace/private/inputs/boot_images/boot_linux_v3265_gpu_h3_cp_set_mode_probe.img`
- Boot SHA256: `cb8c579aa4cc694de363d7e2334c202f255431bba9e4f1a385fe0f2b3094ba84`
- Init after flash: `A90 Linux init 0.11.59 (v3265-gpu-h3-cp-set-mode-probe)`

## What Was Tested

- Kept the V3263 H3 stream: shader payload, direct-render marker, visibility packet trio, zero window offsets, A640
  sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and
  `VPC_SO_OVERRIDE(false)`.
- Added Mesa restore-path `CP_SET_MODE(0)` after pre-draw CCU/cache invalidation and before H3 shader/state/draw
  packets.
- Expected H3 stream size became `262` dwords with `98` state register writes.

## Flash And Health

- Rollback gates were reconfirmed before flash: v2321 SHA matched, v2237 SHA matched, v48 and TWRP recovery artifacts
  existed.
- Pre-flash resident was V3263 and passed `selftest pass=12 warn=1 fail=0`.
- Flash helper confirmed local SHA, recovery push SHA, boot readback SHA, and native-init version/status.
- First explicit post-flash selftest had serial fragment noise but returned rc=0; after restarting the managed bridge,
  selftest was clean: `pass=12 warn=1 fail=0`.
- Post-probe selftest also passed: `selftest pass=12 warn=1 fail=0`.

## Live H3 Result

- Two H3 runs submitted and retired cleanly.
- Confirmed stream identity:
  - `gpu.h3.draw.cp_set_mode=0x63`
  - `gpu.h3.draw.cp_set_mode_value=0x0`
  - `gpu.h3.draw.cmd_write_rc=0`
  - `gpu.h3.draw.pm4_dwords=262`
  - `gpu.h3.draw.state_reg_writes=98`
  - `gpu.h3.draw.submit_rc=0`
  - `gpu.h3.draw.wait_rc=0`
  - `gpu.h3.draw.retired_timestamp=1`
- Readback remained unchanged on both runs:
  - `gpu.h3.draw.result=draw-retired-readback-unchanged`
  - `gpu.h3.draw.readback_changed_count=0`
  - `gpu.h3.draw.readback0=0x20202020`
  - `gpu.h3.draw.readback_center=0x20202020`
- Focused dmesg filter for KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signatures returned no matches.

## Conclusion

- V3266 removes missing Mesa restore-path `CP_SET_MODE(0)` as the primary no-pixel root cause.
- H4 is still not reached.
- Next bounded unit should either build a host-only freedreno Gallium + drm-shim reference environment to generate a
  real `.rd` / cffdump command stream, or continue source-grounded diff around remaining A6xx program/RB state that is
  present in Mesa but absent from H3.

## Safety

- Boot partition only, via checked flash helper.
- No forbidden partition writes.
- No PMIC/GDSC/regulator/GPIO write.
- No proprietary blob, full Mesa compiler port, or KMS presentation.
