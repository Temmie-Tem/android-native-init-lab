# Native Init V3256 GPU H3 Sysmem Bin-Control Live

## Summary

- Cycle: `V3256`
- Live target: `V3255` image, `0.11.54 (v3255-gpu-h3-sysmem-bin-control-probe)`
- Boot image SHA256: `0ccb33c25dcbbf9a8274d2d569c135a48a9ef208bb27e512d0cd73687a651501`
- Result: BOOT/HEALTH PASS, H3 PIXEL PROOF FAIL
- Decision: `sysmem-bin-control-not-primary-no-pixel-root-cause`

## Flash Gate

- Rollback `v2321` SHA256 matched the required value.
- Deeper fallback `v2237` SHA256 matched the required value.
- Final fallback `boot_linux_v48.img` was present.
- TWRP recovery artifacts were present under the private firmware input path.
- Current resident before flash was `0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)` with `selftest pass=12 warn=1 fail=0`.
- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Boot partition prefix readback SHA256 matched the V3255 image SHA256.

## Post-Flash Health

- Native-init flash verify reached `0.11.54 (v3255-gpu-h3-sysmem-bin-control-probe)`.
- A first manual health attempt was accidentally issued in parallel and exhausted the serial bridge transaction lock; this was a host-side bridge framing issue, not a device health failure.
- Restarting the managed serial bridge restored framing.
- After bridge restart, `version`, `status`, and `selftest verbose` all passed with `selftest pass=12 warn=1 fail=0`.
- Explicit post-probe `selftest verbose` again reported `pass=12 warn=1 fail=0`.

## H3 Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Verified V3255 telemetry:

- `gpu.h3.draw.scope=first-triangle-h3-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader`
- `gpu.h3.draw.sp_update_cntl=0x9f`
- `gpu.h3.draw.rb_ccu_cntl=0x10000000`
- `gpu.h3.draw.bin_control_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-bin-size`
- `gpu.h3.draw.gras_sc_bin_cntl=0x2c00000`
- `gpu.h3.draw.rb_cntl=0x2c00000`
- `gpu.h3.draw.pm4_dwords=246`
- `gpu.h3.draw.state_reg_writes=94`

First live run:

- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=30`

Second warm-run check:

- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=13`

Focused dmesg fault filter found no KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature. The broader GPU filter showed expected first-use `a640_zap` firmware load activity and an unrelated modem firmware timeout line.

## Interpretation

V3255 proves the Mesa-style A6xx sysmem render-pass bin controls were emitted and reached live code:
the command stream grew to `pm4_dwords=246`, state writes grew to `94`, and both `GRAS_SC_BIN_CNTL` and `RB_CNTL`
reported `0x02c00000`. The H3 draw still submitted and retired cleanly, but sysmem readback stayed unchanged across
cold and warm runs.

This removes missing `GRAS_SC_BIN_CNTL/RB_CNTL` sysmem bin controls as the primary no-pixel root cause. `RB_CCU_CNTL=0x10000000`
is also source-verified for A640 sysmem mode by local Mesa trace and config calculation. Remaining work should avoid broad
register sweeping and instead diff H3 against a real fd6 sysmem draw stream. One concrete mismatch already visible from
`fd6_emit_sysmem_prep()` is `VPC_SO_OVERRIDE(false)`: current H3 still reports `vpc_so_override=0x1`.
