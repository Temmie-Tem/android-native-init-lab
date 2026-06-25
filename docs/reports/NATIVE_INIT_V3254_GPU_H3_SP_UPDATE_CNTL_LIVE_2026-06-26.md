# Native Init V3254 GPU H3 SP_UPDATE_CNTL Live

## Summary

- Cycle: `V3254`
- Live target: `V3253` image, `0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)`
- Boot image SHA256: `1395721839c41ac07ff41379fabaa298d40479b237384add1bcfb6c1837d5769`
- Result: BOOT/HEALTH PASS, H3 PIXEL PROOF FAIL
- Decision: `draw-local-sp-update-cntl-not-primary-no-pixel-root-cause`

## Flash Gate

- Rollback `v2321` SHA256 matched the required value.
- Deeper fallback `v2237` SHA256 matched the required value.
- Final fallback `boot_linux_v48.img` was present.
- TWRP recovery artifacts were present under the private firmware input path.
- Current resident before flash was `0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)` with `selftest pass=12 warn=1 fail=0`.
- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Boot partition prefix readback SHA256 matched the V3253 image SHA256.

## Post-Flash Health

- Native-init flash verify reached `0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)`.
- The first explicit `selftest verbose` after flash hit a serial protocol framing failure (`A90P1 END marker not found`) with stray `AT` text; the device was not reflashed.
- Restarting the managed serial bridge restored framing.
- After bridge restart, `version`, `status`, and `selftest verbose` all passed with `selftest pass=12 warn=1 fail=0`.
- Explicit post-probe `selftest verbose` again reported `pass=12 warn=1 fail=0`.

## H3 Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Verified V3253 telemetry:

- `gpu.h3.draw.scope=first-triangle-h3-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader`
- `gpu.h3.draw.sp_update_cntl_source=mesa-freedreno-a6xx-fd6-program-and-draw-stateobj`
- `gpu.h3.draw.sp_update_cntl=0x9f`
- `gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x`
- `gpu.h3.draw.vs_shader_dwords=32`
- `gpu.h3.draw.fs_shader_dwords=32`
- `gpu.h3.draw.vs_shader_instrlen=1`
- `gpu.h3.draw.fs_shader_instrlen=1`
- `gpu.h3.draw.pm4_dwords=242`
- `gpu.h3.draw.state_reg_writes=92`

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
- `gpu.h3.draw.total_elapsed_ms=12`

Focused dmesg filter found no KGSL/GPU fault, hang, snapshot, or timeout signature. It showed expected first-use
`a640_zap` firmware load activity and an unrelated WLAN firmware timeout line.

## Interpretation

V3253 proves the draw-local Mesa-style `SP_UPDATE_CNTL=0x0000009f` state bootstrap was emitted and reached live code:
the command stream grew to `pm4_dwords=242`, the telemetry reported `sp_update_cntl=0x9f`, and the H3 draw still submitted
and retired cleanly. The sysmem readback remained unchanged across cold and warm runs.

This removes the missing draw-local `SP_UPDATE_CNTL=0x9f` packet as the primary no-pixel root cause. Remaining work should
stay shader-byte frozen and focus on a tighter non-shader packet delta: restore-state ordering / `CP_SET_MODE` behavior,
or the sysmem MRT / CCU visibility path.
