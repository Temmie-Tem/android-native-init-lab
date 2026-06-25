# Native Init V3272 GPU H3 SP Frontend Prog ID Source Build

## Summary

- Cycle: `V3272`
- Track: GPU H3 first-triangle SP front-end program-id/system-value state before H4 readback proof.
- Decision: `v3272-gpu-h3-sp-frontend-prog-id-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3272_gpu_h3_sp_frontend_prog_id_probe.img`
- Boot SHA256: `6ff91c08ee0a866c251675780a23b94834aed44ccd26a3ead4f3e4e9022b0b96`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.62 (v3272-gpu-h3-sp-frontend-prog-id-probe)`

## Included Delta

- Keeps the V3270 shader payload, direct-render marker, visibility packet trio, zero window offsets, CP_SET_MODE(0), A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, `VPC_SO_OVERRIDE(false)`, triangle raster mode, SP const enables, and `SP_PS_OUTPUT_CNTL=0xfcfcfc00`.
- Adds the A6xx fd6 FS-input/program-id state group missing from H3: `SP_PS_INITIAL_TEX_LOAD_CNTL`, `SP_PS_WAVE_CNTL`, `SP_LB_PARAM_LIMIT`, and `SP_REG_PROG_ID_0..3`.
- Uses current H3 constant-FS semantics: no varyings, no fragment sysvals, invalid `0xfc` regids for unused face/sample/IJ/coord slots, and `SP_PS_INITIAL_TEX_LOAD_CNTL=0x8` for zero prefetch with IJ writes disabled.
- Leaves cffdump's `SP_REG_PROG_ID_1=0xfcfcfc00` and `SP_PS_WAVE_CNTL=0x3` out of this probe because that reference FS uses `bary.f`; H3's current FS does not.
- Expected PM4 size rises from `270` to `282` dwords; expected 3D state register writes rise from `100` to `106`.
- Removes the preserved V3268 DOOM engine entry before packing V3272 to keep the boot image under the 64MiB gate.

## Source Basis

- Local A6xx XML defines `SP_PS_WAVE_CNTL` at `0xb980`, `SP_LB_PARAM_LIMIT` at `0xb982`, and `SP_REG_PROG_ID_0..3` at `0xb983..0xb986` as A6xx draw registers.
- Local Mesa `fd6_program.cc::emit_fs_inputs()` emits this state for every FS, using `INVALID_REG=0xfc` for absent front-face/sample-mask/IJ/coord system values.
- The A640 triangle `.rd` summary confirms the same register family is present in a real fd6 draw; H3 previously emitted only `SP_REG_PROG_ID_3`.
- HLSQ round-4 audit: old `HLSQ_CONTROL_*` / `HLSQ_*_CNTL` names are not present in this A6xx XML/fd6 draw path; the actionable front-end gap is the SP wave/program-id group.

## Safety

- Boot partition only through `native_init_flash.py` in the live step.
- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.
- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.

## Validation

- `py_compile`: V3272 builder and focused source contract test.
- `unittest`: V3272 GPU H3 SP front-end source contract and H3 source compatibility tests.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3272 identity plus SP front-end program-id telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.
- `git diff --check`: PASS before commit.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h3-sp-frontend-prog-id-probe-candidate`.
