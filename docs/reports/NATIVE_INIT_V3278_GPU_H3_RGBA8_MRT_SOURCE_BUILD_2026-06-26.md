# Native Init V3278 GPU H3 RGBA8 MRT Source Build

## Summary

- Cycle: `V3278`
- Track: GPU H3 first-triangle cffdump RGBA8 MRT color-target probe before H4 readback proof.
- Decision: `v3278-gpu-h3-rgba8-mrt-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3278_gpu_h3_rgba8_mrt_probe.img`
- Boot SHA256: `c51ac3a3e10114d605fd5ffb4d0a27b6c6a5a2e4259ab9282389f2f5aa5f8e71`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.65 (v3278-gpu-h3-rgba8-mrt-probe)`

## Included Delta

- Keeps the V3276 direct-render/sysmem/rasterizer/varying-IJ baseline intact.
- Changes H3 MRT0 color target from `FMT6_32_FLOAT` (`0x4a`) to the A640 cffdump sysmem triangle format `FMT6_8_8_8_8_UNORM` (`0x30`).
- Adds explicit telemetry for `color_format_source`, `SP_PS_MRT[0].REG`, `RB_MRT0_BUF_INFO`, and `offscreen=rgba8-linear-128x128`.
- Does not emit speculative A6XX HLSQ program-control registers: the local A6XX XML/generated headers expose only HLSQ load-state/static unknowns, and the local cffdump triangle does not show a legacy HLSQ control block.
- Expected PM4 size remains `306` dwords; expected 3D state register writes remain `118`; VFD draw-local writes remain `14`.

## Source Basis

- Local A640 cffdump sysmem triangle uses `SP_PS_MRT[0].REG=0x00000030` and `RB_MRT[0].BUF_INFO` color format `0x30` for the RGBA8 MRT0 color target.
- Local cffdump and `fd6_program.cc` agree that `RB_PS_OUTPUT_CNTL=0` is normal when depth/samplemask/stencil are not written, while `SP_PS_OUTPUT_CNTL=0xfcfcfc00` and `RB/SP_PS_MRT_CNTL=1` are already present in H3.
- The shader bytes and current color-format contract are checked by the updated H3 shader audit using the local Mesa `ir3-disasm` path when present.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3278 builder, shader audit, and focused source contract tests.
- `unittest`: V3278 GPU H3 RGBA8 MRT source contract and H3 shader-byte audit.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3278 identity plus RGBA8 MRT telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-rgba8-mrt-probe-candidate`.
