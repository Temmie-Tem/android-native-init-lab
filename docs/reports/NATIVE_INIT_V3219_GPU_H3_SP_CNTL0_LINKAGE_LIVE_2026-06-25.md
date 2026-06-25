# Native Init V3219 GPU H3 SP CNTL0 Linkage Live Validation

## Summary

- Cycle: `V3219`
- Candidate under test: `V3218`
- Track: GPU first-triangle H3.3 live validation.
- Decision: `v3219-gpu-h3-sp-cntl0-linkage-live-no-pixel`
- Result: PASS for boot health and H3 command retirement; still NOT H4 triangle proof.
- Resident after validation: `A90 Linux init 0.11.36 (v3218-gpu-h3-sp-cntl0-linkage-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3218_gpu_h3_sp_cntl0_linkage_probe.img`
- Boot SHA256: `f94aabf1476d89612fcc6260b0640948ee7d852c2192039bc451b84f162c4b57`

## Flash

Pre-flash gates passed:

- Rollback V2321 SHA256 matched the pinned clean USB-identity checkpoint.
- Deeper fallback V2237 SHA256 matched the pinned supplicant checkpoint.
- Final fallback V48 was present.
- TWRP recovery artifacts were present.
- Current resident before flash was V3216 and status/selftest were clean, `fail=0`.

The V3218 image was flashed through `workspace/public/src/scripts/revalidation/native_init_flash.py` only. The helper
confirmed the local marker, image size `66052096`, pinned SHA256, recovery-side remote SHA256, boot write, and boot
readback SHA256. The device rebooted to system and native-init version/status verification passed.

## Health

- Resident after flash: `0.11.36 / v3218-gpu-h3-sp-cntl0-linkage-probe`.
- Post-flash status: boot OK, storage mounted RW, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- First post-flash selftest command completed on-device but the host parser missed the `A90P1 END` marker due to serial
  prompt noise; retry with slow input passed with `pass=12 warn=1 fail=0`.
- Post-probe status: boot OK, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- Post-probe `selftest`: `pass=12 warn=1 fail=0`.

Device-specific serial, storage UUID, and network endpoint values were intentionally omitted from this report.

## H3 Live Result

`gpu g0-fwclass-prepare` initially returned `busy` because the auto menu was active, then completed successfully with
`--hide-on-busy`; the final telemetry included `gpu.g0.fwclass_prepare.result=ok`.

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

```text
gpu.h3.draw.scope=first-triangle-h3-sp-cntl0-linkage-mov-f32-shader
gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler
gpu.h3.draw.sp_cntl0_source=mesa-freedreno-a6xx-sp-footprint-mergedregs
gpu.h3.draw.sp_vs_cntl0=0x100080
gpu.h3.draw.sp_ps_cntl0=0x81000080
gpu.h3.draw.ir3_end_opcode_hi=0x3000000
gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x20444000
gpu.h3.draw.fs_color_f32_bits=0x3f800000
gpu.h3.draw.color_output_mask=0x1
gpu.h3.draw.offscreen=f32-linear-128x128
gpu.h3.draw.readback_change_expected=1
gpu.h3.draw.result=draw-retired-readback-unchanged
gpu.h3.draw.timed_out=0
gpu.h3.draw.submit_rc=0
gpu.h3.draw.wait_rc=0
gpu.h3.draw.wait_errno=0
gpu.h3.draw.retired_timestamp=1
gpu.h3.draw.fence_poll_rc=1
gpu.h3.draw.color_format=0x4a
gpu.h3.draw.pm4_dwords=170
gpu.h3.draw.state_reg_writes=62
gpu.h3.draw.vfd_reg_writes=8
gpu.h3.draw.readback_changed_count=0
gpu.h3.draw.readback0=0x20202020
gpu.h3.draw.readback_center=0x20202020
gpu.h3.draw.total_elapsed_ms=454
```

Latest bridge log scan showed the expected V3218 H3 draw result and `readback_changed_count=0`. No `GPU PAGE FAULT`,
CP opcode fault, KGSL fault, Adreno fault, SMMU/IOMMU fault, or GPU hang signature was found in the current bridge log.

## Interpretation

V3218 proves the H3 envelope still retires after replacing the shared `SP_*_CNTL_0=0x80` placeholder with
Mesa-derived minimal A6xx SP control values:

- VS: `FULLREGFOOTPRINT=1|MERGEDREGS` -> `0x00100080`.
- FS: `FULLREGFOOTPRINT=1|INOUTREGOVERLAP|MERGEDREGS` with zero-valued `THREAD64` -> `0x81000080`.

Because readback remains unchanged despite `readback_change_expected=1`, SP footprint/merged-reg control is not the
remaining primary blocker. The next bounded unit should focus on FS output/MRT linkage, raster/depth/stencil/coverage
enables, or a Mesa-diffed minimal draw-state packet gap before claiming H4.

H4 remains unclaimed until interior pixels change and exterior pixels remain clear.

## Safety

- Boot partition only; no forbidden partition write.
- Flash path only: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- No rollback was needed for V3218.
- No PMIC, regulator, GDSC, GPIO, power-rail, proprietary blob, EGL, OpenCL, exploit, or full Mesa compiler path was
  attempted.
- KGSL work stayed child-bounded with timeout/reap cleanup.
