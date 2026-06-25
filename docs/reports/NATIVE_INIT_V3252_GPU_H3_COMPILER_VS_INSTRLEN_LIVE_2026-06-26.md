# Native Init V3252 GPU H3 Compiler VS/Instrlen Live

## Summary

- Cycle: `V3252`
- Live target: `V3251` image, `0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)`
- Boot image SHA256: `ac608fe5914a834b5f895c79ee28b4c4d5212b8fbdbcec0e73408fde92226426`
- Result: BOOT/HEALTH PASS, H3 PIXEL PROOF FAIL
- Decision: `shader-bytes-and-instrlen-not-primary-no-pixel-root-cause`

## Flash Gate

- Rollback `v2321` SHA256 matched the required value.
- Deeper fallback `v2237` SHA256 matched the required value.
- Final fallback `boot_linux_v48.img` was present.
- TWRP recovery artifacts were present under the private firmware input path.
- Current resident before flash was `0.11.51 (v3249-gpu-h3-cache-invalidate-probe)` with `selftest pass=12 warn=1 fail=0`.
- Flash path: checked helper `workspace/public/src/scripts/revalidation/native_init_flash.py` only.
- Boot partition prefix readback SHA256 matched the V3251 image SHA256.

## Post-Flash Health

- Native-init verify reached `0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)`.
- `status` reported boot OK and `selftest pass=12 warn=1 fail=0`.
- Explicit post-probe `selftest verbose` again reported `pass=12 warn=1 fail=0`.

## H3 Live Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Verified V3251 telemetry:

- `gpu.h3.draw.scope=first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader`
- `gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x`
- `gpu.h3.draw.vs_shader_dwords=32`
- `gpu.h3.draw.fs_shader_dwords=32`
- `gpu.h3.draw.vs_shader_instr_count=3`
- `gpu.h3.draw.fs_shader_instr_count=2`
- `gpu.h3.draw.vs_shader_instrlen=1`
- `gpu.h3.draw.fs_shader_instrlen=1`
- `gpu.h3.draw.ir3_instr_align=16`
- `gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x204cc002`
- `gpu.h3.draw.ir3_mov_u32u32_r0w_hi=0x204cc003`

First live run:

- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=29`

Second warm-run check:

- `gpu.h3.draw.result=draw-retired-readback-unchanged`
- `gpu.h3.draw.submit_rc=0`
- `gpu.h3.draw.wait_rc=0`
- `gpu.h3.draw.retired_timestamp=1`
- `gpu.h3.draw.readback_changed_count=0`
- `gpu.h3.draw.readback0=0x20202020`
- `gpu.h3.draw.readback_center=0x20202020`
- `gpu.h3.draw.total_elapsed_ms=12`

Focused dmesg filter found no KGSL/GPU fault, hang, snapshot, or timeout signature. It did show expected first-use
`a640_zap` firmware load activity during the first H3 probe.

## Interpretation

V3251 proves the operator-requested shader-byte unit was applied live: the VS is now the Mesa reference minimal
`mov.u32u32 r0.z, 0x3f800000`; `mov.u32u32 r0.w, 0x3f800000`; `end` payload, the copied shader BO remains
128-byte aligned, and the hardware state uses Mesa-style `instrlen=1` for `SP_*_INSTR_SIZE` and CP_LOAD_STATE6
shader load units. The draw still submits, retires, and leaves the sysmem readback unchanged.

This removes the hand-assembled shader bytes and shader-load unit count as the primary no-pixel root cause. Remaining
work should move back to a concrete Mesa first-draw packet diff outside shader bytes: draw-state bootstrap ordering,
`CP_SET_MODE` / `SP_UPDATE_CNTL` style restore state, or the sysmem MRT / CCU visibility path. Do not continue blind
shader opcode probing without a new disassembler-backed mismatch.
