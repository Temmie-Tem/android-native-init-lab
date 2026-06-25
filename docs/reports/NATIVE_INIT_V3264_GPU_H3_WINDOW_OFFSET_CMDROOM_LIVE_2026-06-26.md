# Native Init V3264 GPU H3 Window Offset Cmdroom Live

## Summary

- Cycle: `V3264`
- Track: GPU H3 first-triangle sysmem-prep ordering before H4 readback proof.
- Decision: `v3264-gpu-h3-window-offset-cmdroom-live-no-pixel`
- Result: NO PIXEL
- Device flash: `yes`, through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flashed image: `workspace/private/inputs/boot_images/boot_linux_v3263_gpu_h3_window_offset_cmdroom_probe.img`
- Boot SHA256: `f38f2fdb7cb71cabc6603e606bcd28965715e128f8211bf767f47f851da7f3d8`
- Init after flash: `A90 Linux init 0.11.58 (v3263-gpu-h3-window-offset-cmdroom-probe)`

## What Was Tested

- Kept the V3259 shader payload, direct-render marker, visibility packet trio, A640 sysmem RB_CCU value, sysmem bin
  controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.
- Kept Mesa sysmem-prep zero window offsets: `RB_WINDOW_OFFSET=0`, `RB_RESOLVE_WINDOW_OFFSET=0`,
  `SP_WINDOW_OFFSET=0`, and `TPL1_WINDOW_OFFSET=0`.
- Raised the shared PM4 command guard from `256` to `320` dwords so the expected `260`-dword stream can be assembled.

## Flash And Health

- Rollback gates were reconfirmed before flash: v2321 SHA matched, v2237 SHA matched, v48 and TWRP recovery artifacts
  existed.
- Flash helper confirmed local SHA, recovery push SHA, boot readback SHA, and native-init version/status.
- First explicit post-flash selftest hit a host-side serial END-marker framing failure, then passed after restarting the
  managed bridge: `selftest pass=12 warn=1 fail=0`.
- Post-probe selftest also passed: `selftest pass=12 warn=1 fail=0`.

## Live H3 Result

- Two H3 runs submitted and retired cleanly.
- Confirmed stream identity:
  - `gpu.h3.draw.rb_window_offset=0x0`
  - `gpu.h3.draw.rb_resolve_window_offset=0x0`
  - `gpu.h3.draw.sp_window_offset=0x0`
  - `gpu.h3.draw.tpl1_window_offset=0x0`
  - `gpu.h3.draw.cmd_write_rc=0`
  - `gpu.h3.draw.pm4_dwords=260`
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

- V3263/V3264 fixes the V3262 PM4 guard failure and creates a valid H3 no-pixel datapoint.
- Zero window-offset sysmem-prep packets and command-buffer room are not the primary no-pixel root cause.
- Next bounded unit should capture and diff a real Mesa fd6 sysmem single-triangle command stream against this H3 stream.
  If a capture remains unavailable, inspect whether Mesa emits any per-MRT render-component/write-enable register that is
  not equivalent to the already-programmed `RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and
  `RB_MRT0_CONTROL.COMPONENT_ENABLE` path.

## Safety

- Boot partition only, via checked flash helper.
- No forbidden partition writes.
- No PMIC/GDSC/regulator/GPIO write.
- No proprietary blob, full Mesa compiler port, or KMS presentation.
