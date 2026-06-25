# Native Init V3243 GPU H3 Direct Render Marker Live

## Summary

- Source build: `V3242`
- Live cycle: `V3243`
- Track: GPU H3 first-triangle direct-render marker validation.
- Result: `draw-retired-readback-unchanged`
- H4 reached: `no`
- Device flash: `yes`, boot partition only via `native_init_flash.py`.
- Init: `A90 Linux init 0.11.48 (v3242-gpu-h3-direct-render-marker-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3242_gpu_h3_direct_render_marker_probe.img`
- Boot SHA256: `eb472fa77edfe20cfeeb5dd280279ba1203e2d4e3fd34d236d81e780bcb5ef13`
- Rollback target kept available: `boot_linux_v2321_usb_clean_identity_rodata.img`

## Flash And Health

- Pre-flash rollback SHA checks matched `v2321` and `v2237`; `boot_linux_v48.img` and the TWRP recovery image were present.
- Pre-flash resident was `0.11.47 (v3240-gpu-h3-sample-location-probe)` with `selftest fail=0`.
- `native_init_flash.py --from-native` verified local Android boot magic, pushed the sealed image in TWRP recovery, wrote only `/dev/block/by-name/boot`, and read back the boot prefix SHA256 as `eb472fa77edfe20cfeeb5dd280279ba1203e2d4e3fd34d236d81e780bcb5ef13`.
- Post-flash native verification passed as `0.11.48 (v3242-gpu-h3-direct-render-marker-probe)`.
- Post-flash `status` reported `selftest: pass=12 warn=1 fail=0`; a separate short `selftest` also returned `pass=12 warn=1 fail=0`.

## Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Direct-render marker telemetry matched V3242:

- `gpu.h3.draw.scope=first-triangle-h3-direct-render-marker-r1-footprint2-mov-f32-shader`
- `gpu.h3.draw.render_marker_source=mesa-freedreno-a6xx-fd6-set-render-mode-rm6-direct-render`
- `gpu.h3.draw.cp_set_marker=0x1`
- `gpu.h3.draw.rb_ccu_cntl=0x10000000`
- `gpu.h3.draw.pm4_dwords=233`
- `gpu.h3.draw.state_reg_writes=92`

Result:

- `gpu.g0.materialize.fwclass_prepare_attempted=1`
- `gpu.g0.fwclass_prepare.result=ok`
- `gpu.h3.draw.materialize_rc=0`
- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.timed_out=0`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=31`

Post-probe `selftest` stayed `pass=12 warn=1 fail=0`. Post-probe `gpu g0-status` showed `/dev/kgsl-3d0` materialized and the firmware cache path active. The focused dmesg filter found the expected `a640_zap` load and an unrelated WLAN firmware timeout, but no KGSL/GPU fault, hang, snapshot, or GPU timeout signature.

## Decision

V3242/V3243 removes the missing `CP_SET_MARKER(RM6_DIRECT_RENDER)` hypothesis as the primary no-pixel root cause. The packet is present, the draw submits and retires, but the MRT readback still remains unchanged. Do not continue treating CP render-mode entry as the blocker.

The next bounded unit should move to the remaining upstream shader/output contract checks before another broad register sweep: verify the hand-assembled ir3 VS writes the clip-space position to the actual position output consumed by VPC, and verify the FS output register/MRT contract under the current `r1` split. LRZ is already programmed disabled in the state stream and RB CCU sysmem control is now present, so those are lower-priority unless new evidence reopens them.
