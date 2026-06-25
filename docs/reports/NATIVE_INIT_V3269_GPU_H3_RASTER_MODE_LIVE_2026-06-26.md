# Native Init V3269 GPU H3 Raster Mode Live

## Summary

- Cycle: `V3269`
- Track: GPU H3 first-triangle polygon raster-mode live validation.
- Result: `draw-retired-readback-unchanged`
- H4 first-triangle proof: `not reached`
- Flashed image: `A90 Linux init 0.11.60 (v3268-gpu-h3-raster-mode-probe)`
- Boot SHA256: `8fc356e60545ad36e412367d40b4da6f6f9a9766c6251369684f187c49323240`
- Source build report: `docs/reports/NATIVE_INIT_V3268_GPU_H3_RASTER_MODE_SOURCE_BUILD_2026-06-26.md`

## Flash Gate

- Built with the checked V3268 build script and recorded SHA256 before flash.
- Rollback images were present and SHA-verified for `v2321` and `v2237`; final fallback `v48` was present.
- TWRP/recovery artifacts were present under `workspace/private/inputs/firmware/twrp/`.
- Flashed only the boot partition via `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Remote boot readback SHA matched the local image SHA.
- Post-flash version confirmed `0.11.60 (v3268-gpu-h3-raster-mode-probe)`.
- Post-flash status/selftest passed after one managed bridge restart cleared host-side serial fragment noise.

## Live Probe

Command:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py --hide-on-busy gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Run 1:

- `gpu.h3.draw.scope=first-triangle-h3-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader`
- `gpu.h3.draw.raster_mode_source=mesa-freedreno-a6xx-fd6-rasterizer-polymode-triangles`
- `gpu.h3.draw.vpc_rast_cntl=0x3`
- `gpu.h3.draw.pc_dgen_rast_cntl=0x3`
- `gpu.h3.draw.pm4_dwords=266`
- `gpu.h3.draw.state_reg_writes=100`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.total_elapsed_ms=29`

Run 2:

- `gpu.h3.draw.vpc_rast_cntl=0x3`
- `gpu.h3.draw.pc_dgen_rast_cntl=0x3`
- `gpu.h3.draw.pm4_dwords=266`
- `gpu.h3.draw.state_reg_writes=100`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.total_elapsed_ms=12`

## Health

- Focused dmesg filter for `kgsl|gpu|gmu|a640|fault|hang|snapshot|timeout`: no matching fault/hang/snapshot/timeout lines.
- Post-probe `selftest verbose`: `pass=12 warn=1 fail=0`.

## Decision

Adding Mesa A6xx polygon raster-mode state made the H3 stream more complete and was validated on-device, but it did not produce pixels. Missing `VPC_RAST_CNTL` / `PC_DGEN_RAST_CNTL` is therefore not the primary no-pixel root cause.

Next bounded unit should continue with real Mesa command-stream/source diff work and avoid re-testing the now-ruled-out CCU magic, bin-control, component-register, CP_SET_MODE, window-offset, visibility-packet, and raster-mode hypotheses.
