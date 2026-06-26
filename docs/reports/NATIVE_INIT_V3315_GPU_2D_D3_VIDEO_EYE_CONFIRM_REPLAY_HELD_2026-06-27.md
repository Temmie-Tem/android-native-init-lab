# Native Init V3315 GPU 2D D3 Video Eye-Confirm Replay Held

## Summary

- Cycle: `V3315`
- Track: GPU accelerated 2D D3, operator eye-confirm replay.
- Decision: `v3315-d3-eye-confirm-replay-held-device-pass`
- Result: PASS for replaying the V3315 Bad Apple GPU-blit path to KMS and holding it for 60 s.
- Device flash: `no`.
- Boot image touched: `none`.
- Resident: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`.
- Visual close: pending operator statement that the held GPU-blit frame looked correct on the physical panel.

## Preconditions

- Existing resident was V3315; no rebuild or flash was required.
- The managed serial bridge was available on `/dev/ttyACM0`.
- Pre-replay resident check returned `0.11.87` with build `v3315-gpu-2d-d3-video-semantic-edge-tolerance`.
- Pre-replay selftest: `pass=12 warn=1 fail=0`.
- The previous V3315 live report already proved the flashed image SHA and rollback-gated flash path.

## Replay Command

The replay hid the menu and used the existing V3315 command with a 60 s hold window:

```text
cmdv1 hide
cmdv1 gpu d3-video-texture-present-probe --preset badapple --start-frame 515 --frames 60 --timeout-ms 120000 --hold-ms 60000 --materialize-devnode
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
- `gpu.d3.video.elapsed_ns=2006104583`
- `gpu.d3.video.fps_milli=29908`
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
- `A90P1 END seq=16 cmd=gpu rc=0 errno=0 duration_ms=62042 flags=0x0 status=ok`

Stage timing:

- `gpu.d3.video.timing.read.avg_us=6`
- `gpu.d3.video.timing.read.max_us=41`
- `gpu.d3.video.timing.texture.avg_us=739`
- `gpu.d3.video.timing.texture.max_us=3601`
- `gpu.d3.video.timing.gpu_wait.avg_us=533`
- `gpu.d3.video.timing.gpu_wait.max_us=640`
- `gpu.d3.video.timing.readback.avg_us=0`
- `gpu.d3.video.timing.readback.max_us=3`
- `gpu.d3.video.timing.copy.avg_us=19457`
- `gpu.d3.video.timing.copy.max_us=30911`
- `gpu.d3.video.timing.present.avg_us=10301`
- `gpu.d3.video.timing.present.max_us=11174`
- `gpu.d3.video.timing.total.avg_us=33432`
- `gpu.d3.video.timing.total.max_us=42563`

## Post Validation

- Post-replay selftest: `pass=12 warn=1 fail=0`.
- Focused post-replay dmesg tail filter matched no GPU/adreno/KGSL fault, hang, snapshot, opcode, SMMU/IOMMU, or
  page-fault signature.
- The dmesg filter command returned only the expected Android linker warning about `/linkerconfig/ld.config.txt`.

## Conclusion

The existing V3315 D3 path was successfully replayed with a 60 s hold and the semantic gate passed again. Telemetry
proves that Bad Apple cache frames were uploaded as textures, rendered through the KGSL textured-quad path, copied to
KMS, and presented at roughly 30 fps. The remaining rung-② close condition is operator eye confirmation that the held
GPU-blit image looked correct on the physical panel.
