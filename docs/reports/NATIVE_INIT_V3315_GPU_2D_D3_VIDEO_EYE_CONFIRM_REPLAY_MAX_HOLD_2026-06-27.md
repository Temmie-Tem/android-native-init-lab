# Native Init V3315 GPU 2D D3 Video Eye-Confirm Replay Max Hold

## Summary

- Cycle: `V3315`
- Track: GPU accelerated 2D D3, operator eye-confirm replay.
- Decision: `v3315-d3-eye-confirm-replay-max-hold-device-pass`
- Result: PASS for replaying the V3315 Bad Apple GPU-blit path to KMS and holding it for the current maximum 60 s.
- Device flash: `no`.
- Boot image touched: `none`.
- Resident: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`.
- Visual close: pending operator statement that the held GPU-blit frame looked correct on the physical panel.

## Preconditions

- Worktree was clean at the start of this replay iteration.
- Existing resident was V3315; no rebuild or flash was required.
- The managed serial bridge was available on `/dev/ttyACM0`.
- Pre-replay resident check returned `0.11.87` with build `v3315-gpu-2d-d3-video-semantic-edge-tolerance`.
- Pre-replay selftest: `pass=12 warn=1 fail=0`.

## Hold Limit

An attempted 120 s hold was rejected by the native guard:

```text
gpu.d3.video.error=bad-hold max_ms=60000
A90P1 END seq=22 cmd=gpu rc=-22 errno=22 duration_ms=0 flags=0x0 status=error
```

No rendering, flash, partition write, or recovery action was involved in that rejected command. The replay was then
rerun with the supported maximum hold value, `--hold-ms 60000`.

## Replay Command

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
- `gpu.d3.video.elapsed_ns=1999648385`
- `gpu.d3.video.fps_milli=30005`
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
- `A90P1 END seq=23 cmd=gpu rc=0 errno=0 duration_ms=62032 flags=0x0 status=ok`

Stage timing:

- `gpu.d3.video.timing.read.avg_us=5`
- `gpu.d3.video.timing.read.max_us=47`
- `gpu.d3.video.timing.texture.avg_us=742`
- `gpu.d3.video.timing.texture.max_us=3592`
- `gpu.d3.video.timing.gpu_wait.avg_us=532`
- `gpu.d3.video.timing.gpu_wait.max_us=638`
- `gpu.d3.video.timing.readback.avg_us=0`
- `gpu.d3.video.timing.readback.max_us=3`
- `gpu.d3.video.timing.copy.avg_us=19466`
- `gpu.d3.video.timing.copy.max_us=26531`
- `gpu.d3.video.timing.present.avg_us=10165`
- `gpu.d3.video.timing.present.max_us=11572`
- `gpu.d3.video.timing.total.avg_us=33325`
- `gpu.d3.video.timing.total.max_us=38231`

## Post Validation

- Post-replay selftest: `pass=12 warn=1 fail=0`.
- Focused post-replay dmesg tail filter matched no GPU/adreno/KGSL fault, hang, snapshot, opcode, SMMU/IOMMU, or
  page-fault signature.
- The dmesg filter command returned only the expected Android linker warning about `/linkerconfig/ld.config.txt`.

## Conclusion

V3315 was replayed again with the supported maximum 60 s hold. Telemetry confirms the same semantic pass as the prior
V3315 replay: 64/64 semantic samples, one bounded edge-tolerant match, no semantic mismatches, no non-binary output
pixels, and clean post-replay health. The remaining rung-② close condition is still operator eye confirmation that the
held GPU-blit image looked correct on the physical panel.
