# Native Init V3210 GPU H2 3D State Probe Source Build

## Summary

- Cycle: `V3210`
- Track: GPU first-triangle H2a: A6xx fixed-function 3D state submit/retire, with no draw.
- Decision: `v3210-gpu-h2-3d-state-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3210_gpu_h2_3d_state_probe.img`
- Boot SHA256: `0d84aeda172b114ac2eaae30b413b3ef3909af2cd9df78c0e981dc5993e9e2c1`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3208_gpu_h1_shader_state_probe.img`
- Init: `A90 Linux init 0.11.32 (v3210-gpu-h2-3d-state-probe)`

## Included Delta

- Adds `gpu h2-3d-state-probe` after the device-proven G0-G5 first-light ladder and the V3208 H1 shader-state upload probe.
- Reuses the bounded child-only KGSL open/ioctl envelope from G3/G4: context, GPUOBJ alloc/mmap/sync, command submit, timestamp fence, wait, readtimestamp, cleanup.
- Allocates a private 128x128 u32 offscreen GPU object and submits a no-draw PM4 stream that programs GRAS viewport/scissor, RB MRT/output, VPC, PC, VFD, and SP output-state registers.
- The command stream deliberately excludes `CP_DRAW_INDX_OFFSET`, shader execution, readback verification, and KMS presentation. This proves only that the fixed-function 3D state packet stream can retire without the parent entering KGSL.
- The final boot image preserves the V3208 ramdisk contents and overlays only the new `/init`, the helper, and `bin/a90_doomgeneric_private_engine_v3210`; this avoids regenerating missing private ACDB deploy-plan intermediates while keeping the known-good bundled audio files.

## H0 Recon Basis

- Mesa/freedreno A6xx source points the first-triangle path at `fd6_emit.cc` for GRAS/RB/VPC/VFD/SP fixed-function state and `fd6_draw.cc` for the later non-indexed `CP_DRAW_INDX_OFFSET` auto-index draw.
- Mesa register XML provides the A6xx GRAS/RB/VPC/PC/VFD/SP register offsets and PM4 packet enum values used here.
- Decision boundary: keep this rung below draw execution and below real shader execution. Do not pull in Mesa's full ir3 compiler, proprietary EGL/GLES blobs, OpenCL, or exploit work.

## Safety

- Boot partition only through `native_init_flash.py` in any future live step.
- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.
- No GDSC/regulator/PMIC/GPIO/power-rail write is included.
- No draw, triangle rasterization, shader execution, readback verification, compute grid, zero-copy dmabuf, or KMS GPU-plane sharing is included in H2a.
- Parent process does not enter KGSL `open()` or `ioctl()`; the child is timeout-guarded and killed on timeout.

## Source Basis

- Mesa source repository: `https://docs.mesa3d.org/repository.html`.
- Freedreno driver overview: `https://docs.mesa3d.org/drivers/freedreno.html`.
- A6xx fixed-function emit path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.
- A6xx shader/program state retained from H1: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- A6xx draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.

## Validation

- `py_compile`: V3210 builder and focused H2 source test.
- `unittest`: V3210 GPU H2 source contract.
- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3210 identity, G0-G5/H1 baseline markers, and H2 fixed-function 3D state markers.
- Ramdisk overlay check: V3208 bundled audio manifest remains present and the V3210 DOOM engine helper is present.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h2-3d-state-probe-candidate`.
