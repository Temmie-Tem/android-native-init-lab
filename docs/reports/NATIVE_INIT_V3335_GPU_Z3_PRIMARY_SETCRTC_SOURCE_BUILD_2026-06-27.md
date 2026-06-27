# Native Init V3335 GPU Z3 Primary SETCRTC Source Build

- Cycle: `V3335`
- Decision: `v3335-gpu-z3-primary-setcrtc-source-build-pass`
- Init: `A90 Linux init 0.11.103 (v3335-gpu-z3-primary-setcrtc)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`
- Boot SHA256: `e7e0240e7894e9bd54a0a4fd5a3bf267b126097a5177ccd17686076528ea736b`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3334_gpu_z3_atomic_allow_modeset.img`

## Change

- Stops the overlay-plane variant loop and adds `gpu z3-imported-scanout-primary-probe`.
- Creates a full-panel KMS dumb scanout framebuffer, exports it as PRIME, imports the same BO into KGSL, and renders the monitor graph directly into that scanout target.
- Presents the imported framebuffer through the primary CRTC with `SETCRTC`, holds it for visual confirmation, then restores the previous base framebuffer before cleanup.
- Makes the GPU 2D present sampler stride-aware so panel pitch padding is handled without a CPU copy.

## Validation Contract

- Command: `gpu z3-imported-scanout-primary-probe --timeout-ms 60000 --hold-ms 12000 --materialize-devnode`
- PASS requires full-panel KMS dumb create/map, PRIME export, KGSL import, GPU render semantic proof, `kms.present_rc=0`, `kms.restore_rc=0`, no KMS copy, positive hold, clean RMFB/dumb cleanup, and post-probe `selftest fail=0`.
- No PMIC/GDSC/regulator/GPIO/backlight write, proprietary blob, EGL/GLES/OpenCL, forbidden partition, or raw flash path is introduced.

## Static Validation

- `py_compile`: V3335 builder and focused source test.
- Unit tests: V3335 focused source contract plus Z3 regression contracts.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3335 identity plus primary SETCRTC telemetry.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-z3-primary-setcrtc-candidate`.
