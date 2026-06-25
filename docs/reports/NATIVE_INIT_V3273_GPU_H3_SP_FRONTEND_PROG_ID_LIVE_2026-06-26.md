# Native Init V3273 GPU H3 SP Frontend Prog ID Live

## Summary

- Cycle: `V3273`
- Track: GPU H3 first-triangle SP front-end program-id/system-value state live validation.
- Source build report: `docs/reports/NATIVE_INIT_V3272_GPU_H3_SP_FRONTEND_PROG_ID_SOURCE_BUILD_2026-06-26.md`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3272_gpu_h3_sp_frontend_prog_id_probe.img`
- Boot SHA256: `6ff91c08ee0a866c251675780a23b94834aed44ccd26a3ead4f3e4e9022b0b96`
- Init: `A90 Linux init 0.11.62 (v3272-gpu-h3-sp-frontend-prog-id-probe)`
- Result: BOOT/HEALTH PASS, H3 PIXEL PROOF FAIL
- H4 first-triangle proof: `not reached`

## Flash And Health

- Rollback gates were reconfirmed before flash:
  `v2321` SHA matched, `v2237` SHA matched, `v48` existed, and TWRP recovery artifacts were present.
- Flashed only the checked V3272 boot artifact through `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Flash helper confirmed local SHA, recovery push SHA, boot block readback SHA, and post-reboot native-init version/status.
- Post-flash health:
  `version` reported `0.11.62`; `status` reported `BOOT OK`; `selftest verbose` reported `pass=12 warn=1 fail=0`.
- Validation note: one host-side accidental parallel serial command caused an A90P1 framing/lock timeout during health collection. The bridge recovered immediately; all subsequent health and probe commands were run sequentially and passed framing.

## Live H3 Result

Two H3 runs were executed with:

```text
python3 workspace/public/src/scripts/revalidation/a90ctl.py --timeout 30 --hide-on-busy gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Both runs applied the V3272 state delta:

- `gpu.h3.draw.scope=first-triangle-h3-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader`
- `gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x8`
- `gpu.h3.draw.sp_ps_wave_cntl=0x0`
- `gpu.h3.draw.sp_lb_param_limit=0x7`
- `gpu.h3.draw.sp_reg_prog_id_0=0xfcfcfcfc`
- `gpu.h3.draw.sp_reg_prog_id_1=0xfcfcfcfc`
- `gpu.h3.draw.sp_reg_prog_id_2=0xfcfcfcfc`
- `gpu.h3.draw.sp_reg_prog_id_3=0xfcfc`
- `gpu.h3.draw.pm4_dwords=282`
- `gpu.h3.draw.state_reg_writes=106`

Both runs retired without timeout:

- Run 1: `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `readback_changed_count=0`,
  `readback0=0x20202020`, `readback_center=0x20202020`, `total_elapsed_ms=29`.
- Run 2: `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `readback_changed_count=0`,
  `readback0=0x20202020`, `readback_center=0x20202020`, `total_elapsed_ms=12`.

Post-probe `selftest verbose` stayed clean: `pass=12 warn=1 fail=0`.

Host-side dmesg filtering over `busybox dmesg` showed no new KGSL page fault, GPU hang, or IOMMU fault signature around the H3 runs. The visible GPU lines were firmware load/reset messages; an unrelated CMA allocation failure appeared before the first H3 draw and did not block the probe from retiring.

## Conclusion

V3272 removed a real A6xx SP front-end/program-id state gap: H3 now explicitly writes the current constant-FS-compatible `SP_PS_INITIAL_TEX_LOAD_CNTL`, `SP_PS_WAVE_CNTL`, `SP_LB_PARAM_LIMIT`, and `SP_REG_PROG_ID_0..3` group. That did not produce pixels. Missing SP front-end/system-value regid invalidation is therefore not the primary H3 no-pixel root cause.

Next bounded unit should stay with the real fd6 `.rd`/cffdump diff and avoid re-testing the ruled-out legacy HLSQ names. The strongest remaining source-grounded deltas are the clip/guardband/SU group (`GRAS_CL_CNTL=0xc0`, `GRAS_CL_GUARDBAND_CLIP_ADJ=0x0007fdff`, `GRAS_SU_CNTL=0x814`) and any direct-sysmem-compatible subset of the fd6 fragment interpolation state, while keeping GMEM/UBWC-only flag-buffer packets out of H3 unless the target architecture changes.
