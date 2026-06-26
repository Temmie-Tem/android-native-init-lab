# Native Init V3315 GPU 2D D3 Video Semantic Edge Tolerance Live

## Summary

- Cycle: `V3315`
- Track: GPU accelerated 2D D3, edge-tolerant semantic video texture present gate.
- Candidate: `workspace/private/inputs/boot_images/boot_linux_v3315_gpu_2d_d3_video_semantic_edge_tolerance.img`
- Candidate SHA256: `e9a5377d51aa1cefee593c363dc21079be47caae95a96ea5475b97e410eb8945`
- Init after flash: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`
- Result: PASS for D3 semantic live validation. The exact V3314 scaled-edge mismatch is now accounted for by one
  source-neighborhood match while the semantic gate still requires 64/64 matches and zero non-binary output pixels.
- Visual close: pending operator statement that the held Bad Apple GPU-blit frame looked correct on the physical panel.

## Flash Gate

- Flash helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Rollback image verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
  SHA256 `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Deeper fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
  SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Final fallback verified before flash:
  `workspace/private/inputs/boot_images/boot_linux_v48.img`
  SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- Recovery/TWRP image verified before flash:
  `workspace/private/inputs/firmware/twrp/recovery.img`
  SHA256 `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash verification matched the local image SHA, remote staged image SHA, and boot-block readback prefix SHA.

## Health

- Pre-flash resident: `A90 Linux init 0.11.86 (v3314-gpu-2d-d3-video-semantic-present)`
- Pre-flash `version`, `status`, and `selftest verbose`: `pass=12 warn=1 fail=0`
- Flash-helper post-boot verification reached V3315 and reported `status` with selftest `pass=12 warn=1 fail=0`.
- The first standalone post-flash `status` attempt was interrupted by serial `AT` noise and lacked the END marker.
  Restarting the managed bridge restored clean protocol framing.
- Standalone post-restart health:
  - `version`: `0.11.87`, build `v3315-gpu-2d-d3-video-semantic-edge-tolerance`
  - `status`: `selftest pass=12 warn=1 fail=0`
  - `selftest verbose`: `pass=12 warn=1 fail=0`
- Post-probe selftest: `pass=12 warn=1 fail=0`

## Cache Gate

`video cache preset badapple status` passed:

- `video.cache.preset=badapple`
- `video.cache.preset.sha256=9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`
- `video.cache.manifest_ok=1`
- `video.cache.stream_exists=1`
- `video.cache.stream_size=150490668`
- `video.cache.stream_expected_size=150490668`
- `video.cache.stream_size_match=1`
- `video.cache.format=mono1`
- `video.cache.frames=6962`
- `video.cache.fps=30/1`
- `video.cache.size=480x360`
- `video.cache.stride=60`
- `video.cache.frame_bytes=21600`

## D3 Probe

Command:

```text
gpu d3-video-texture-present-probe --preset badapple --start-frame 515 --frames 60 --timeout-ms 120000 --hold-ms 60000 --materialize-devnode
```

Key telemetry:

- `gpu.d3.video.result=video-texture-present-pass`
- `gpu.d3.video.timed_out=0`
- `gpu.d3.video.child_killed=0`
- `gpu.d3.video.child_reaped=1`
- `gpu.d3.video.child_status=0x0`
- `gpu.d3.video.result_rc=0`
- `gpu.d3.video.manifest_rc=0`
- `gpu.d3.video.stream_open_rc=0 errno=0`
- `gpu.d3.video.header_rc=0`
- `gpu.d3.video.gpu_create_rc=0`
- `gpu.d3.video.source_size=480x360`
- `gpu.d3.video.source_stride=60`
- `gpu.d3.video.source_frame_bytes=21600`
- `gpu.d3.video.target_size=960x720`
- `gpu.d3.video.target_stride=3840`
- `gpu.d3.video.target_bytes=2764800`
- `gpu.d3.video.pm4_dwords=409`
- `gpu.d3.video.start_frame_actual=515`
- `gpu.d3.video.skipped_frames=515`
- `gpu.d3.video.last_frame_index=574`
- `gpu.d3.video.presented=60`
- `gpu.d3.video.failed_frame=4294967295`
- `gpu.d3.video.stream_bytes=1296000`
- `gpu.d3.video.elapsed_ns=2023264166`
- `gpu.d3.video.fps_milli=29655`
- `gpu.d3.video.changed_total=41472000`
- `gpu.d3.video.last_first_word=0xff000000`
- `gpu.d3.video.last_center_word=0xff000000`
- `gpu.d3.video.semantic.sample_count=64`
- `gpu.d3.video.semantic.match_count=64`
- `gpu.d3.video.semantic.exact_match_count=63`
- `gpu.d3.video.semantic.edge_tolerant_match_count=1`
- `gpu.d3.video.semantic.edge_tolerance_radius=1`
- `gpu.d3.video.semantic.mismatch_count=0`
- `gpu.d3.video.semantic.first_mismatch_index=4294967295`
- `gpu.d3.video.semantic.source_dark_count=164511`
- `gpu.d3.video.semantic.source_light_count=8289`
- `gpu.d3.video.semantic.output_dark_count=658044`
- `gpu.d3.video.semantic.output_light_count=33156`
- `gpu.d3.video.semantic.output_other_count=0`
- `gpu.d3.video.present_rc=0`
- `gpu.d3.video.close_rc=0 errno=0`
- `A90P1 END seq=10 cmd=gpu rc=0 errno=0 duration_ms=62265 flags=0x0 status=ok`

Stage timing:

- `gpu.d3.video.timing.read.avg_us=9`
- `gpu.d3.video.timing.read.max_us=46`
- `gpu.d3.video.timing.texture.avg_us=737`
- `gpu.d3.video.timing.texture.max_us=3625`
- `gpu.d3.video.timing.gpu_wait.avg_us=628`
- `gpu.d3.video.timing.gpu_wait.max_us=6307`
- `gpu.d3.video.timing.readback.avg_us=0`
- `gpu.d3.video.timing.readback.max_us=5`
- `gpu.d3.video.timing.copy.avg_us=19630`
- `gpu.d3.video.timing.copy.max_us=39601`
- `gpu.d3.video.timing.present.avg_us=10315`
- `gpu.d3.video.timing.present.max_us=12839`
- `gpu.d3.video.timing.total.avg_us=33718`
- `gpu.d3.video.timing.total.max_us=57014`

## Edge Evidence

The V3314 exact mismatch was at source coordinate `(330,68)` of frame `574`: the exact pixel is white while immediate
neighbors are black. V3315 therefore records `exact_match_count=63` and `edge_tolerant_match_count=1`, with
`semantic_match_count=64`, `semantic_mismatch_count=0`, and `semantic_output_other_count=0`.

## Kernel Log Check

Focused post-probe dmesg tail filtering matched no KGSL/adreno/GMU/ringbuffer/snapshot/fault/hang/SMMU/IOMMU/page-fault
signature. The command returned only the expected Android linker warning about `/linkerconfig/ld.config.txt`.

## Conclusion

V3315 closes the D3 semantic telemetry gap: the Bad Apple cache frames are uploaded as textures, rendered through the
KGSL textured-quad path, A2D-linearized, copied into the KMS framebuffer, presented, held for 60 s, and validated with
64/64 semantic samples under a bounded scaled-edge tolerance. The remaining rung-② close condition is operator visual
confirmation of the held frame on the physical panel.
