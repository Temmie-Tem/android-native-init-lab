# Native Init V3221 GPU H3 Raster Coverage Live Validation

## Summary

- Cycle: `V3221`
- Candidate under test: `V3220`
- Track: GPU first-triangle H3.4 live validation.
- Decision: `v3221-gpu-h3-raster-coverage-live-no-pixel`
- Result: PASS for boot health and H3 command retirement; still NOT H4 triangle proof.
- Resident after validation: `A90 Linux init 0.11.37 (v3220-gpu-h3-raster-coverage-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3220_gpu_h3_raster_coverage_probe.img`
- Boot SHA256: `0ef76e157d47ed5e71f756b5b7bef540300e9bcf3f8d70817a078e70460e594e`

## Flash

Pre-flash gates passed:

- Rollback V2321 SHA256 matched the pinned clean USB-identity checkpoint.
- Deeper fallback V2237 SHA256 matched the pinned supplicant checkpoint.
- Final fallback V48 was present.
- TWRP recovery artifacts were present.
- Current resident before flash was V3218 and version/status/selftest were clean, `fail=0`.

The V3220 image was flashed through `workspace/public/src/scripts/revalidation/native_init_flash.py` only. The helper
confirmed the local marker, image size `66052096`, pinned SHA256, recovery-side remote SHA256, boot write, and boot
readback SHA256. The device rebooted to system and native-init version/status verification passed.

## Health

- Resident after flash: `0.11.37 / v3220-gpu-h3-raster-coverage-probe`.
- Post-flash status: boot OK, storage mounted RW, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- Post-flash `selftest`: command completed with `rc=0` and the later post-probe retry printed `pass=12 warn=1 fail=0`.
- One `gpu g0-fwclass-prepare` attempt was discarded because serial input was polluted into `cmTdv1...` and parsed as
  `unknown command: pu`; the resident stayed healthy. Retrying through the clean prompt with normal input and
  `--hide-on-busy` completed successfully.
- Post-probe status: boot OK, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- Post-probe `selftest`: `pass=12 warn=1 fail=0`.

Device-specific serial, storage UUID, and network endpoint values were intentionally omitted from this report.

## H3 Live Result

`gpu g0-fwclass-prepare` completed successfully with final telemetry `gpu.g0.fwclass_prepare.result=ok`.

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

```text
gpu.h3.draw.scope=first-triangle-h3-raster-coverage-mov-f32-shader
gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler
gpu.h3.draw.sp_cntl0_source=mesa-freedreno-a6xx-sp-footprint-mergedregs
gpu.h3.draw.sp_vs_cntl0=0x100080
gpu.h3.draw.sp_ps_cntl0=0x81000080
gpu.h3.draw.raster_coverage_source=mesa-freedreno-a6xx-gras-rb-msaa-defaults
gpu.h3.draw.gras_sc_ras_msaa_cntl=0x0
gpu.h3.draw.gras_sc_dest_msaa_cntl=0x4
gpu.h3.draw.gras_sc_screen_scissor_cntl=0x0
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
gpu.h3.draw.pm4_dwords=176
gpu.h3.draw.state_reg_writes=65
gpu.h3.draw.vfd_reg_writes=8
gpu.h3.draw.readback_changed_count=0
gpu.h3.draw.readback0=0x20202020
gpu.h3.draw.readback_center=0x20202020
gpu.h3.draw.total_elapsed_ms=455
```

Latest bridge log scan showed the expected V3220 H3 draw result and `readback_changed_count=0`. No `GPU PAGE FAULT`,
CP opcode fault, KGSL fault, Adreno fault, SMMU/IOMMU fault, or GPU hang signature was found in the current bridge log.

## Interpretation

V3220 proves the H3 envelope still retires after adding the concrete Mesa-derived GRAS raster coverage defaults:

- `GRAS_SC_RAS_MSAA_CNTL=0x00000000`.
- `GRAS_SC_DEST_MSAA_CNTL=0x00000004`.
- `GRAS_SC_SCREEN_SCISSOR_CNTL=0x00000000`.

Because readback remains unchanged despite `readback_change_expected=1`, this raster coverage default gap is not the
remaining primary blocker. The next bounded unit should focus on FS output/MRT linkage, VPC/RB output state, or a
Mesa-diffed minimal draw-state packet gap before claiming H4.

H4 remains unclaimed until interior pixels change and exterior pixels remain clear.

## Safety

- Boot partition only; no forbidden partition write.
- Flash path only: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- No rollback was needed for V3220.
- No PMIC, regulator, GDSC, GPIO, power-rail, proprietary blob, EGL, OpenCL, exploit, or full Mesa compiler path was
  attempted.
- KGSL work stayed child-bounded with timeout/reap cleanup.
