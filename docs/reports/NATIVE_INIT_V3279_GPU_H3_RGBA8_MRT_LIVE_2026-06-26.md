# Native Init V3279 GPU H3 RGBA8 MRT Live

## Summary

- Cycle: `V3279`
- Track: GPU H3 first-triangle RGBA8 MRT color-target live validation.
- Source build report: `docs/reports/NATIVE_INIT_V3278_GPU_H3_RGBA8_MRT_SOURCE_BUILD_2026-06-26.md`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3278_gpu_h3_rgba8_mrt_probe.img`
- Boot SHA256: `c51ac3a3e10114d605fd5ffb4d0a27b6c6a5a2e4259ab9282389f2f5aa5f8e71`
- Init: `A90 Linux init 0.11.65 (v3278-gpu-h3-rgba8-mrt-probe)`
- Result: BOOT/HEALTH PASS, H3 PIXEL PROOF FAIL
- H4 first-triangle proof: `not reached`

## Flash And Health

- Rollback gates were reconfirmed before flash:
  `v2321` SHA matched, `v2237` SHA matched, `v48` existed, and `workspace/private/inputs/firmware/twrp/recovery.img`
  existed.
- Flashed only the checked V3278 boot artifact through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flash helper confirmed local SHA, recovery push SHA, boot block readback SHA, and post-reboot native-init
  version/status.
- Post-flash health:
  `version` reported `0.11.65`; `status` reported `BOOT OK`; `selftest verbose` reported `pass=12 warn=1 fail=0`.

## Live H3 Result

Two H3 runs were executed with:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py --input-mode slow --timeout 120 gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Both runs applied the V3278 state delta:

- `gpu.h3.draw.scope=first-triangle-h3-rgba8-mrt-cffdump-diff-varying-ij-vpc-linkage-...`
- `gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs`
- `gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-mrt0`
- `gpu.h3.draw.sp_ps_mrt_reg0=0x30`
- `gpu.h3.draw.rb_mrt0_buf_info=0x30`
- `gpu.h3.draw.offscreen=rgba8-linear-128x128`
- `gpu.h3.draw.color_format=0x30`
- `gpu.h3.draw.pm4_dwords=306`
- `gpu.h3.draw.state_reg_writes=118`
- `gpu.h3.draw.vfd_reg_writes=14`

Both runs retired without timeout:

- Run 1: `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `readback_changed_count=0`,
  `readback0=0x20202020`, `readback_center=0x20202020`, `total_elapsed_ms=29`.
- Run 2: `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `readback_changed_count=0`,
  `readback0=0x20202020`, `readback_center=0x20202020`, `total_elapsed_ms=12`.

Post-probe `selftest verbose` stayed clean: `pass=12 warn=1 fail=0`.

Focused dmesg filtering over `busybox dmesg` showed no KGSL page fault, GPU hang, IOMMU/SMMU fault, CP opcode fault,
snapshot, or timeout signature around the H3 runs. Visible lines were expected first-use `a640_zap` load/reset plus an
unrelated modem firmware timeout; the H3 submissions still retired cleanly.

## Conclusion

V3278 removed the cffdump-diff color-target mismatch by switching H3 MRT0 from `FMT6_32_FLOAT` to
`FMT6_8_8_8_8_UNORM`. The draw still retired with unchanged readback, so the previous float-vs-RGBA8 MRT mismatch is
not the primary no-pixel cause.

Next bounded unit should stop isolated HLSQ/output/raster guesses and use a real fd6 sysmem single-triangle
`.rd`/cffdump packet diff against the current H3 stream, admitting only direct-sysmem-compatible missing packet groups.
