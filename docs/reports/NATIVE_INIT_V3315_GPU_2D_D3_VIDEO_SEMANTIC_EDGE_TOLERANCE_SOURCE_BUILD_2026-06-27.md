# Native Init V3315 GPU 2D D3 Video Semantic Edge Tolerance Source Build

## Summary

- Cycle: `V3315`
- Track: GPU accelerated 2D D3, semantic video texture present gate.
- Decision: `v3315-gpu-2d-d3-video-semantic-edge-tolerance-source-build-pass`
- Result: PASS
- Device flash: `no` in this build unit.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3315_gpu_2d_d3_video_semantic_edge_tolerance.img`
- Boot SHA256: `e9a5377d51aa1cefee593c363dc21079be47caae95a96ea5475b97e410eb8945`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3314_gpu_2d_d3_video_semantic_present.img`
- Init: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`

## Included Delta

- Extends `gpu d3-video-texture-present-probe` with `--start-frame N` so visual close can hold a high-contrast Bad Apple segment instead of the black intro.
- Adds edge-tolerant final-frame semantic validation: 64 target samples are mapped back to the source mono1 frame, and exact mismatches may match a 3x3 source-neighborhood when the sample lands on a scaled texture edge.
- Reports exact-match count, edge-tolerant match count, edge radius, final source dark/light counts, final output dark/light/other counts, start-frame telemetry, skipped-frame count, and last presented frame index.
- Strengthens the D3 pass predicate from `presented>0 && changed_total>0` to include `semantic_sample_count=64`, `semantic_match_count=64`, `exact_match_count + edge_tolerant_match_count = 64`, `semantic_mismatch_count=0`, and `semantic_output_other_count=0`.

## D3 Gate

- Source preset: `badapple`, SHA256 `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`, geometry `480x360 mono1`.
- Visual-close command starts at frame `515` and presents 60 frames before the hold.
- PASS requires `gpu.d3.video.result=video-texture-present-pass`, `presented>0`, `changed_total>0`, timing telemetry, and the edge-tolerant semantic sample gate.
- This is still a recoverable probe path, not a new default menu policy.

## Safety

- KGSL and KMS work runs in a timeout-guarded child; the parent can kill the worker on timeout.
- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.
- Boot partition only through `native_init_flash.py` in the live step.

## Validation

- `py_compile`: V3315 builder and focused source test.
- `unittest`: V3315 D3 edge-tolerant semantic source contract plus V3314 semantic-present baseline coverage.
- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.
- Marker check: generated boot image contains V3315 identity plus D3 semantic telemetry.
- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.

## Metadata

- Helper flags: ``
- Init extra flags: ``
- Textured FS SHA256: `4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3`
- D0 reference: `v3304-fd6-texture-reference-recon`
- D1 shader gate: `v3305-verified-textured-fs-shader-bytes`
- D2 live baseline: `v3311-d2-realframe-texture-live-pass`
- D3 live baseline: `v3314-d3-semantic-exact-edge-mismatch`
- Semantic edge tolerance radius: `1`
- Candidate type: `gpu-2d-d3-video-semantic-edge-tolerance-candidate`.
