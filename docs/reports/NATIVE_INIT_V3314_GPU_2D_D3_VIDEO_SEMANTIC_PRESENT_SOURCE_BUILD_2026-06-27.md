# Native Init V3314 GPU 2D D3 Video Semantic Present Source Build

## Summary

- Cycle: `V3314`
- Track: GPU accelerated 2D D3, semantic video texture present gate.
- Decision: `v3314-gpu-2d-d3-video-semantic-present-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3314_gpu_2d_d3_video_semantic_present.img`
- Boot SHA256: `1bf80b18bfe56b3cfe7fcc37c5d10566775524aa564b2efec88d1dcf159bf617`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3313_gpu_2d_d3_video_texture_present_fork_fix.img`
- Init: `A90 Linux init 0.11.86 (v3314-gpu-2d-d3-video-semantic-present)`

## Included Delta

- Extends `gpu d3-video-texture-present-probe` with `--start-frame N` so visual close can hold a high-contrast Bad Apple segment instead of the black intro.
- Adds final-frame semantic validation: 64 target samples are mapped back to the source mono1 frame and must match the expected black/white value.
- Reports final source dark/light counts, final output dark/light/other counts, start-frame telemetry, skipped-frame count, and last presented frame index.
- Strengthens the D3 pass predicate from `presented>0 && changed_total>0` to include `semantic_sample_count=64`, `semantic_match_count=64`, `semantic_mismatch_count=0`, and `semantic_output_other_count=0`.

## D3 Gate

- Source preset: `badapple`, SHA256 `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`, geometry `480x360 mono1`.
- Visual-close command starts at frame `515` and presents 60 frames before the hold.
- PASS requires `gpu.d3.video.result=video-texture-present-pass`, `presented>0`, `changed_total>0`, timing telemetry, and the semantic sample gate.
- This is still a recoverable probe path, not a new default menu policy.

## Safety

- KGSL and KMS work runs in a timeout-guarded child; the parent can kill the worker on timeout.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3314 builder and focused source test.
- `unittest`: V3314 D3 semantic source contract plus V3313 fork-fix baseline coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3314 identity plus D3 semantic telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Textured FS SHA256: `4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3`
- D0 reference: `v3304-fd6-texture-reference-recon`
- D1 shader gate: `v3305-verified-textured-fs-shader-bytes`
- D2 live baseline: `v3311-d2-realframe-texture-live-pass`
- D3 live baseline: `v3313-d3-video-texture-present-live-pass`
- Candidate type: `gpu-2d-d3-video-semantic-present-candidate`.
