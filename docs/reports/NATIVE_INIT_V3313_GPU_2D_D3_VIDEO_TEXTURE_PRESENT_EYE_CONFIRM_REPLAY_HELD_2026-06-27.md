# Native Init V3313 GPU 2D D3 Video Texture Present Eye-Confirm Replay Held

## Summary

- Cycle: `V3313`
- Track: GPU accelerated 2D D3, operator eye-confirm replay.
- Decision: `v3313-d3-eye-confirm-replay-held-device-pass`
- Result: PASS for replaying the existing V3313 Bad Apple GPU-blit path to KMS and holding it for 60 s.
- Device flash: `no`.
- Boot image touched: `none`.
- Resident: `A90 Linux init 0.11.85 (v3313-gpu-2d-d3-video-texture-present-fork-fix)`.
- Visual close: pending operator statement that the held GPU-blit frame looked correct on the panel.

## Preconditions

- Existing resident was V3313; no rebuild or flash was required.
- The bridge was available on `/dev/ttyACM0`.
- The previous V3313 live report already proved the flashed image SHA and rollback-gated flash path.

## Replay Command

The replay used the existing V3313 command with a longer hold window:

```text
cmdv1 hide
cmdv1 gpu d3-video-texture-present-probe --preset badapple --frames 60 --timeout-ms 120000 --hold-ms 60000 --materialize-devnode
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
- `gpu.d3.video.presented=60`
- `gpu.d3.video.failed_frame=0`
- `gpu.d3.video.stream_bytes=1296000`
- `gpu.d3.video.elapsed_ns=1988214634`
- `gpu.d3.video.fps_milli=30177`
- `gpu.d3.video.timing.read.avg_us=6`
- `gpu.d3.video.timing.read.max_us=32`
- `gpu.d3.video.timing.texture.avg_us=653`
- `gpu.d3.video.timing.texture.max_us=3125`
- `gpu.d3.video.timing.gpu_wait.avg_us=530`
- `gpu.d3.video.timing.gpu_wait.max_us=620`
- `gpu.d3.video.timing.readback.avg_us=0`
- `gpu.d3.video.timing.readback.max_us=3`
- `gpu.d3.video.timing.copy.avg_us=16585`
- `gpu.d3.video.timing.copy.max_us=29815`
- `gpu.d3.video.timing.present.avg_us=13794`
- `gpu.d3.video.timing.present.max_us=14288`
- `gpu.d3.video.timing.total.avg_us=33134`
- `gpu.d3.video.timing.total.max_us=40858`
- `gpu.d3.video.changed_total=41472000`
- `gpu.d3.video.last_first_word=0xff000000`
- `gpu.d3.video.last_center_word=0xff000000`
- `gpu.d3.video.kms_begin_rc=0`
- `gpu.d3.video.present_rc=0`
- `gpu.d3.video.close_rc=0 errno=0`
- `A90P1 END seq=12 cmd=gpu rc=0 errno=0 duration_ms=62010 flags=0x0 status=ok`

## Post Validation

- Post-replay resident: `A90 Linux init 0.11.85 (v3313-gpu-2d-d3-video-texture-present-fork-fix)`.
- Post-replay selftest: `pass=12 warn=1 fail=0`.
- Focused post-replay dmesg tail filter matched no GPU/adreno/KGSL fault, hang, snapshot, opcode, SMMU/IOMMU, or
  page-fault signature.

## Conclusion

The existing V3313 D3 path was successfully replayed with a 60 s hold. Telemetry proves that Bad Apple cache frames
were uploaded as textures, rendered through the GPU textured-quad path, copied to KMS, and presented at roughly 30 fps.
The remaining rung-② close condition is operator eye confirmation that the held GPU-blit image looked correct.
