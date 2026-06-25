# Native Init V3235 GPU H3 Shader Output Live

## Summary

- Cycle: `V3235`
- Track: GPU first-triangle H3 live validation for V3234.
- Candidate boot: `workspace/private/inputs/boot_images/boot_linux_v3234_gpu_h3_shader_output_probe.img`
- Candidate SHA256: `d9dc5774c2722272bcc96021ec1c6c82cb9aa25f9010acbc7855b23a0787d0ad`
- Flashed init: `A90 Linux init 0.11.44 (v3234-gpu-h3-shader-output-probe)`
- Decision: `v3235-gpu-h3-shader-output-live-timeout-regression`
- Result: FAIL for H3/H4; boot health remained OK.

## Flash And Health

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Flash route: native init bridge to TWRP recovery, boot partition only.
- Local image magic: Android boot image magic present.
- Remote pushed image SHA256: `d9dc5774c2722272bcc96021ec1c6c82cb9aa25f9010acbc7855b23a0787d0ad`
- Boot block readback SHA256: `d9dc5774c2722272bcc96021ec1c6c82cb9aa25f9010acbc7855b23a0787d0ad`
- Post-flash version/status: passed; device booted `0.11.44`.
- Post-flash selftest: `pass=12 warn=1 fail=0`.

## H3 Probe

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

```text
gpu.h3.draw.scope=first-triangle-h3-shader-output-r1-mov-f32-shader
gpu.h3.draw.shader_payload=hand-assembled-ir3-r1-output-mov-f32-vs-position-fs-color-no-full-compiler
gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map
gpu.h3.draw.vs_shader_dwords=12
gpu.h3.draw.fs_shader_dwords=8
gpu.h3.draw.vs_output_regid=0x4
gpu.h3.draw.ps_output_regid=0x4
gpu.h3.draw.sp_vs_output_reg0=0xf04
gpu.h3.draw.child_pid=649
gpu.h3.draw.result=timeout
gpu.h3.draw.timed_out=1
gpu.h3.draw.child_killed=1
gpu.h3.draw.child_reaped=1
gpu.h3.draw.child_status=0x9
```

Result:

- H3 regressed from V3232's retired draw to a child timeout (`rc=-110`, duration about `5004ms`).
- No readback proof was produced; H4 remains open.
- Post-probe selftest remained `pass=12 warn=1 fail=0`.
- A dmesg tail fault filter for KGSL/Adreno/GPU fault/hang/snapshot/timeout signatures produced no match.
- A follow-up `gpu g3-noop-submit-probe --timeout-ms 1000 --materialize-devnode` also timed out, indicating the failed H3 run can leave the KGSL queue wedged until reboot even though native-init health remains OK.

## Interpretation

- The r1 output-regid split was not a valid standalone fix.
- The most likely immediate issue is that the shader now writes and exports `r1.*` while `SP_VS_CNTL_0` and `SP_PS_CNTL_0` still use `FULLREGFOOTPRINT=1`. That footprint only covers the original r0-only shader contract.
- Next bounded unit should keep the V3234 r1 split but bump VS/PS full register footprint to `2`, then retest H3. If that restores retirement but still draws no pixels, continue with shader-output/RB linkage; if it still times out, revert the r1 split and move to another Mesa packet delta.

## Safety

- No forbidden partition was touched.
- Flash used only `native_init_flash.py`.
- Rollback images were present before flash; v2321 and v2237 SHA256 matched the AGENTS contract.
- No auto-rollback was triggered because boot, status, and selftest did not regress. V3234 is nevertheless not promoted as a functional GPU baseline.
