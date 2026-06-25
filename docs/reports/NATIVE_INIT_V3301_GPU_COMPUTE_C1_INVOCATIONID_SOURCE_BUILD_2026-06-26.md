# Native Init V3301 GPU Compute C1 Invocationid Source Build

## Summary

- Cycle: `V3301`
- Track: GPU compute demo C1, first live compute dispatch/readback probe.
- Decision: `v3301-gpu-compute-c1-invocationid-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3301_gpu_compute_c1_invocationid_probe.img`
- Boot SHA256: `c4128f367a17f2481866142d79942d958ea19fa34528937dece6edf3d04e7dfa`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3268_gpu_h3_raster_mode_probe.img`
- Init: `A90 Linux init 0.11.75 (v3301-gpu-compute-c1-invocationid-probe)`

## Included Delta

- Embeds the V3300 verified FD640 `kern_invocationid.asm` CS words in native-init.
- Adds `gpu c1-compute-invocationid-probe` with KGSL cmd/shader/UAV/descriptor/event objects.
- Emits the Mesa computerator-style `SP_CS_*`, `LOAD_STATE6` shader/constants/UAV, `RM6_COMPUTE`, and `CP_EXEC_CS` sequence.
- Verifies the 32-word UAV readback contract: `buf[i] == i` for `i=0..31`.

## Safety

- KGSL userspace path only; no KMS present in C1.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3301 builder and focused source test.
- `unittest`: V3301 C1 source contract plus V3300 shader-byte regression coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3301 identity plus C1 compute readback telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Shader SHA256: `7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a`
- Kernel SHA256: `1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a`
- Candidate type: `gpu-compute-c1-invocationid-probe-candidate`.
