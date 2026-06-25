# Native Init V3208 GPU H1 Shader State Probe Source Build

## Summary

- Cycle: `V3208`
- Track: GPU first-triangle H0/H1: A6xx shader processor state upload and CP_LOAD_STATE6 shader preload, with no draw.
- Decision: `v3208-gpu-h1-shader-state-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3208_gpu_h1_shader_state_probe.img`
- Boot SHA256: `ce17810bc9099a2e3b97cacc6299a552bc331355238f18b6b978ac0fb9e06c35`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3204_gpu_g5_kms_blit_probe.img`
- Init: `A90 Linux init 0.11.31 (v3208-gpu-h1-shader-state-probe)`

## Included Delta

- Adds `gpu h1-shader-state-probe` after the device-proven G0-G5 first-light ladder.
- Reuses the bounded child-only KGSL open/ioctl envelope from G3/G4: context, GPUOBJ alloc/mmap/sync, command submit, timestamp fence, wait, readtimestamp, cleanup.
- Uploads separate VS/FS GPU objects and submits a minimal no-draw PM4 stream that sets SP VS/PS base/config/instruction-size registers and emits `CP_LOAD_STATE6_GEOM`/`CP_LOAD_STATE6_FRAG` indirect shader loads.
- The shader payload is deliberately recorded as a no-execute placeholder. This proves object upload/SP state/preload retirement only; it is not yet a pass-through vertex shader, constant-color fragment shader, or triangle proof.
- The final boot image preserves the V3204 ramdisk contents and overlays only the new `/init`, the helper, and `bin/a90_doomgeneric_private_engine_v3208`; this avoids regenerating missing private ACDB deploy-plan intermediates while keeping the known-good bundled audio files.

## H0 Recon Basis

- Mesa/freedreno A6xx source points the first-triangle path at `fd6_program.cc` for SP program state and shader `CP_LOAD_STATE6`, and `fd6_draw.cc` for non-indexed `CP_DRAW_INDX_OFFSET` auto-index draws.
- Mesa register XML provides the A6xx SP VS/PS register offsets and CP packet enum values used here.
- Decision boundary: keep this rung below draw execution until the hand-assembled ir3 payload is proven. Do not pull in Mesa's full ir3 compiler, proprietary EGL/GLES blobs, OpenCL, or exploit work.

## Safety

- Boot partition only through `native_init_flash.py` in any future live step.
- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.
- No GDSC/regulator/PMIC/GPIO/power-rail write is included.
- No draw, rasterizer, readback verification, compute grid, zero-copy dmabuf, or KMS GPU-plane sharing is included in H1.
- Parent process does not enter KGSL `open()` or `ioctl()`; the child is timeout-guarded and killed on timeout.

## Source Basis

- Mesa source repository: `https://docs.mesa3d.org/repository.html`.
- Freedreno driver overview: `https://docs.mesa3d.org/drivers/freedreno.html`.
- A6xx shader/program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.
- A6xx draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.
- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.
- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.

## Validation

- `py_compile`: V3208 builder and focused H1 source test.
- `unittest`: V3208 GPU H1 source contract.
- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3208 identity, G0-G5 baseline markers, and H1 shader-state markers.
- Ramdisk overlay check: V3204 bundled audio manifest remains present and the V3208 DOOM engine helper is present.
- `git diff --check`: PASS.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Candidate type: `gpu-h1-shader-state-probe-candidate`.
