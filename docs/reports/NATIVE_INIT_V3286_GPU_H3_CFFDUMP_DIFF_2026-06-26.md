# Native Init V3286 GPU H3 Cffdump Diff

## Summary

- Cycle: `V3286`
- Track: GPU H3 first-triangle packet-level diff before H4 readback proof.
- Decision: `v3286-gpu-h3-cffdump-diff-host-only-pass`
- Result: PASS
- Device flash: `no`; this is a host-only diff/report unit.
- Input trace: `/tmp/a90-h3-cffdump/triangle_list.rd`
- Trace SHA256: `2fe5c6781058bb698e373bef3d2a9cffe4f04503d9fe3c9f81f2938cdb053011`
- Decoded summary: `/tmp/a90-h3-cffdump/triangle_summary.txt`

## Findings

- The local cffdump `draw[2]` stream is a real A640 triangle draw, but it is a GMEM draw pass with a later resolve. H3 remains a direct-sysmem draw, so GMEM-path registers such as `RB_CCU_CNTL`, `GRAS_SC_BIN_CNTL`, and `RB_CNTL` are contextual and not safe single-register copy targets.
- Already-closed/currently matching H3 state includes `RB_RENDER_CNTL=0x00010010`, `RB_MRT[0].CONTROL=0x780`, `RB_MRT[0].BUF_INFO=0x330`, `SP_PS_OUTPUT_CNTL=0xfcfcfc00`, `SP_PS_MRT[0].REG=0x30`, `VPC_VS_CNTL=0x00ff0408`, and `VPC_PS_CNTL=0xff01ff04`.
- Strongest remaining structural diff is the VFD/VS contract: cffdump uses three fetch/decode streams (`VFD_CNTL_0=0x303`), 36-byte vertex stride, 4-float position/color plus an integer attribute, and `REGID4VTX=r2.y`; current H3 uses one 2-float fetch/decode stream (`VFD_CNTL_0=0x101`), 8-byte stride, `.xy` destination only, and no vertex-id register.
- Smallest remaining direct-sysmem-compatible output-state group is blend/output state: cffdump has `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`; current H3 emits `0` for all three. This is low blast radius, but the reference draw has blending disabled, so it is not proven root cause.
- `SP_VS_CONST_CONFIG` differs (`0x101` reference vs `0x100` H3), but the reference VS uses `c1.x/c1.y` constants while current H3 VS does not. Treat this as part of a coherent reference VS/VFD replay, not a standalone fix.

## Added Tooling

- Added `workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py`.
- Added `tests/test_native_gpu_h3_cffdump_diff_v3286.py`.
- The script parses cffdump `draw[2]` register values, resolves current H3 state from `80_shell_dispatch.inc.c`, classifies remaining deltas, and excludes address, target-size, and GMEM-vs-sysmem differences.

## Validation

- `py_compile`: V3286 cffdump diff script.
- `unittest`: V3286 cffdump diff tests.
- No build or flash was performed.

## Next Bounded Unit

Prefer one of these, in order:

1. A coherent reference-contract VFD/VS unit: replace the H3 vertex payload, VFD fetch/decode layout, and VS input contract together. Do not single-register-copy `VFD_CNTL_0`.
2. A smaller direct-sysmem-safe blend/output-state probe: set `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804` together, with the same H3 timeout and readback guards.
