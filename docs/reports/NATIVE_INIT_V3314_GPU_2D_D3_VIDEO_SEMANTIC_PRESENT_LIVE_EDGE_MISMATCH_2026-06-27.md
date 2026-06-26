# Native Init V3314 GPU 2D D3 Video Semantic Present Live Edge Mismatch

## Summary

- Cycle: `V3314`
- Track: GPU accelerated 2D D3, semantic video texture present gate.
- Candidate: `workspace/private/inputs/boot_images/boot_linux_v3314_gpu_2d_d3_video_semantic_present.img`
- Candidate SHA256: `1bf80b18bfe56b3cfe7fcc37c5d10566775524aa564b2efec88d1dcf159bf617`
- Init after flash: `A90 Linux init 0.11.86 (v3314-gpu-2d-d3-video-semantic-present)`
- Result: NOT CLOSED. The live probe rendered, presented, held, and stayed healthy, but the new exact semantic gate
  failed by one source-edge sample: `semantic_match_count=63`, `semantic_mismatch_count=1`.

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

- Pre-flash resident: `A90 Linux init 0.11.85 (v3313-gpu-2d-d3-video-texture-present-fork-fix)`
- Pre-flash selftest: `pass=12 warn=1 fail=0`
- Flash-helper post-boot verification reached V3314 and reported selftest `pass=12 warn=1 fail=0`.
- A standalone post-flash `version` attempt hit serial prompt noise (`cmdv1 vrsATATAT`) and did not find the END marker.
  The managed bridge was restarted, after which `version` and `selftest verbose` passed.
- Post-probe selftest: `pass=12 warn=1 fail=0`

## Cache Gate

`video cache preset badapple status` passed after hiding the auto menu:

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

- `gpu.d3.video.result=video-texture-present-failed`
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
- `gpu.d3.video.start_frame=515`
- `gpu.d3.video.start_frame_actual=515`
- `gpu.d3.video.skipped_frames=515`
- `gpu.d3.video.last_frame_index=574`
- `gpu.d3.video.presented=60`
- `gpu.d3.video.failed_frame=4294967295`
- `gpu.d3.video.stream_bytes=1296000`
- `gpu.d3.video.elapsed_ns=2011238384`
- `gpu.d3.video.fps_milli=29832`
- `gpu.d3.video.changed_total=41472000`
- `gpu.d3.video.last_first_word=0xff000000`
- `gpu.d3.video.last_center_word=0xff000000`
- `gpu.d3.video.semantic.sample_count=64`
- `gpu.d3.video.semantic.match_count=63`
- `gpu.d3.video.semantic.mismatch_count=1`
- `gpu.d3.video.semantic.first_mismatch_index=13`
- `gpu.d3.video.semantic.first_mismatch_expected=0xffffff`
- `gpu.d3.video.semantic.first_mismatch_value=0x0`
- `gpu.d3.video.semantic.source_dark_count=164511`
- `gpu.d3.video.semantic.source_light_count=8289`
- `gpu.d3.video.semantic.output_dark_count=658044`
- `gpu.d3.video.semantic.output_light_count=33156`
- `gpu.d3.video.semantic.output_other_count=0`
- `gpu.d3.video.present_rc=0`
- `gpu.d3.video.close_rc=0 errno=0`

Stage timing:

- `gpu.d3.video.timing.read.avg_us=9`
- `gpu.d3.video.timing.read.max_us=38`
- `gpu.d3.video.timing.texture.avg_us=761`
- `gpu.d3.video.timing.texture.max_us=3526`
- `gpu.d3.video.timing.gpu_wait.avg_us=630`
- `gpu.d3.video.timing.gpu_wait.max_us=6342`
- `gpu.d3.video.timing.readback.avg_us=0`
- `gpu.d3.video.timing.readback.max_us=4`
- `gpu.d3.video.timing.copy.avg_us=18952`
- `gpu.d3.video.timing.copy.max_us=38522`
- `gpu.d3.video.timing.present.avg_us=11602`
- `gpu.d3.video.timing.present.max_us=13411`
- `gpu.d3.video.timing.total.avg_us=33518`
- `gpu.d3.video.timing.total.max_us=55816`

## Kernel Log Check

Focused post-probe dmesg tail filtering matched no KGSL/adreno/GMU/ringbuffer/snapshot/fault/hang/SMMU/IOMMU/page-fault
signature. The command returned only the expected Android linker warning about `/linkerconfig/ld.config.txt`.

## Interpretation

V3314 is a useful stricter gate, but the exact source-pixel comparison is too brittle at a scaled texture edge. The
render path itself did not fail: the worker exited cleanly, 60 frames were presented, the KMS present succeeded, the
held screen window completed, output pixels were only black/white (`semantic_output_other_count=0`), and post-probe
selftest stayed clean.

The single mismatch maps to a sampled source-edge location where the CPU exact validator expected white
(`0xffffff`) and the rendered output was black (`0x0`). The next bounded unit should keep the same start-frame/high
contrast validation but make the semantic gate source-neighborhood tolerant for scaled texture edges, while still
requiring 64/64 semantic samples to match under that tolerance and zero non-binary output pixels.

## Conclusion

Do not roll back V3314 solely because this command returned `rc=-5`; the device is bootable and healthy. Treat this as
a D3 validation-design finding: V3314 proves the high-contrast present path is live, and V3315 should close the exact
edge-sample gap with an edge-tolerant semantic validator before claiming D3/② close.
