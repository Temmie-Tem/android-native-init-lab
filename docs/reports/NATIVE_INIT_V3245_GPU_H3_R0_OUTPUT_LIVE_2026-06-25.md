# Native Init V3245 GPU H3 R0 Output Live

## Summary

- Source build: `V3244`
- Live cycle: `V3245`
- Track: GPU H3 first-triangle r0 output contract validation.
- Result: `draw-retired-readback-unchanged`
- H4 reached: `no`
- Device flash: `yes`, boot partition only via `native_init_flash.py`.
- Init: `A90 Linux init 0.11.49 (v3244-gpu-h3-r0-output-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3244_gpu_h3_r0_output_probe.img`
- Boot SHA256: `9764d950f93ada582b5b853c17dcf480635df0aeffe5ee90d6cab7845533c66d`
- Rollback target kept available: `boot_linux_v2321_usb_clean_identity_rodata.img`

## Flash And Health

- Pre-flash rollback SHA checks matched `v2321` and `v2237`; `boot_linux_v48.img` and the V3242 base boot were present.
- Pre-flash resident was `0.11.48 (v3242-gpu-h3-direct-render-marker-probe)` with `selftest: pass=12 warn=1 fail=0`.
- `native_init_flash.py --from-native` verified the local marker, pushed the sealed image in TWRP recovery, wrote only `/dev/block/by-name/boot`, and read back the boot prefix SHA256 as `9764d950f93ada582b5b853c17dcf480635df0aeffe5ee90d6cab7845533c66d`.
- Post-flash native verification passed as `0.11.49 (v3244-gpu-h3-r0-output-probe)`.
- Post-flash `status` reported `selftest: pass=12 warn=1 fail=0`; a separate `selftest verbose` also returned `pass=12 warn=1 fail=0`.

## Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

R0-output telemetry matched V3244:

- `gpu.h3.draw.scope=first-triangle-h3-r0-output-full-state-mov-f32-shader`
- `gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler`
- `gpu.h3.draw.vs_output_regid=0x0`
- `gpu.h3.draw.ps_output_regid=0x0`
- `gpu.h3.draw.sp_vs_output_reg0=0xf00`
- `gpu.h3.draw.cp_set_marker=0x1`
- `gpu.h3.draw.rb_ccu_cntl=0x10000000`
- `gpu.h3.draw.pm4_dwords=233`
- `gpu.h3.draw.state_reg_writes=92`

Result:

- `gpu.g0.materialize.fwclass_prepare_attempted=1`
- `gpu.g0.fwclass_prepare.result=ok`
- `gpu.g0.materialize.fwclass_prepare_rc=0`
- `gpu.h3.draw.materialize_rc=0`
- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.timed_out=0`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback_first_changed_index=4294967295`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=29`

Post-probe `selftest verbose` stayed `pass=12 warn=1 fail=0`. The focused dmesg filter found the expected `a640_zap` load and an unrelated modem firmware timeout, but no KGSL/GPU fault, hang, snapshot, or GPU timeout signature.

## Decision

V3244/V3245 removes the simple r1-output-register mismatch hypothesis as the primary no-pixel root cause. With the current full H3 fixed-state envelope, switching VS/PS output regids to `0` and writing the color from FS `r0.x` still submits and retires but leaves the sysmem MRT unchanged.

The next bounded unit should stop toggling output regid alone and prove the remaining shader execution contract more directly: either add a shader/disassembly source audit for the hand-assembled ir3 words and scheduling bits, or use a minimal known-good compiler/disassembler-derived ir3 payload while preserving the same KGSL-direct envelope. Continue avoiding broad downstream register sweeps unless the shader contract is proven.
