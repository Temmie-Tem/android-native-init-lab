# Native Init V3217 GPU H3 Minimal ir3 Mov Shader Live Validation

## Summary

- Cycle: `V3217`
- Candidate under test: `V3216`
- Track: GPU first-triangle H3.2 live validation.
- Decision: `v3217-gpu-h3-minimal-ir3-mov-shader-live-no-pixel`
- Result: PASS for boot health and H3 command retirement; still NOT H4 triangle proof.
- Resident after validation: `A90 Linux init 0.11.35 (v3216-gpu-h3-minimal-ir3-mov-shader-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3216_gpu_h3_minimal_ir3_mov_shader_probe.img`
- Boot SHA256: `594cb31e298ce21605ae9fe4c01f138d2493daf30917d235230dba375f0e5929`

## Flash

Pre-flash gates passed:

- Rollback V2321 SHA256 matched the pinned clean USB-identity checkpoint.
- Deeper fallback V2237 SHA256 matched the pinned supplicant checkpoint.
- Final fallback V48 was present.
- TWRP recovery artifacts were present.
- Current resident before flash was V3214 and status/selftest were clean, `fail=0`.

The V3216 image was flashed through `workspace/public/src/scripts/revalidation/native_init_flash.py` only. The helper
confirmed the local marker, image size `66052096`, pinned SHA256, recovery-side remote SHA256, boot write, and boot
readback SHA256. The device rebooted to system and native-init version/status verification passed.

## Health

- Resident after flash: `0.11.35 / v3216-gpu-h3-minimal-ir3-mov-shader-probe`.
- Post-flash status: boot OK, storage mounted RW, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.
- A first verbose selftest printed `pass=12 warn=1 fail=0` but the host parser missed the END marker due to serial noise.
- Retried version/status completed normally.
- Post-probe `selftest verbose`: `pass=12 warn=1 fail=0`.
- Post-probe status: boot OK, transport ready, display `1080x2400`, selftest `pass=12 warn=1 fail=0`.

Device-specific serial, storage UUID, and network endpoint values were intentionally omitted from this report.

## H3 Live Result

`gpu g0-fwclass-prepare` completed successfully before the draw probe.

Command:

```text
gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode
```

Key telemetry:

```text
gpu.h3.draw.scope=first-triangle-h3-minimal-ir3-mov-f32-shader
gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler
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
gpu.h3.draw.color_format=0x4a
gpu.h3.draw.readback_changed_count=0
gpu.h3.draw.readback0=0x20202020
gpu.h3.draw.readback_center=0x20202020
gpu.h3.draw.fence_poll_rc=1
gpu.h3.draw.total_elapsed_ms=452
```

Latest bridge log scan showed the expected V3216 `minimal-ir3` draw result and `readback_changed_count=0`. No `GPU PAGE
FAULT`, CP opcode fault, KGSL fault, Adreno hang, or GPU hang signature was found in the current bridge log.

## Interpretation

V3216 proves the H3 envelope still retires after replacing the terminator-only shader with a bounded cat1 `mov.f32f32`
payload and switching MRT0 to single-channel `FMT6_32_FLOAT`. Because the readback remains unchanged despite
`readback_change_expected=1`, the remaining H4 gap is no longer just a missing shader terminator.

Most likely next checks:

- VS output/VPC destination mapping: confirm the position output location and `SP_VS_OUTPUT`/`SP_VS_VPC_DEST` values match
  what A6xx expects for clip-space position.
- FS output/MRT linkage: confirm `SP_PS_OUTPUT`, `SP_PS_MRT`, `RB_PS_OUTPUT_MASK`, and `RB_MRT0_CONTROL` are sufficient for
  a one-channel float render target.
- Raster/draw state: confirm no missing draw/rasterizer enable or flush event is preventing color writes despite the fence
  retiring.

H4 remains unclaimed until interior pixels change and exterior pixels remain clear.

## Safety

- Boot partition only; no forbidden partition write.
- Flash path only: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- No rollback was needed for the corrected V3216 image.
- No PMIC, regulator, GDSC, GPIO, power-rail, proprietary blob, EGL, OpenCL, exploit, or full Mesa compiler path was
  attempted.
- KGSL work stayed child-bounded with timeout/reap cleanup.
