# Native Init V3315 GPU 2D D3 Video Eye Confirmed

## Summary

- Cycle: `V3315`
- Track: GPU accelerated 2D D3, operator eye confirmation.
- Decision: `v3315-d3-gpu-accelerated-2d-eye-confirmed-close`
- Result: DONE + EYE-CONFIRMED for GPU-accelerated 2D rung ② D0→D3.
- Device flash: `no`.
- Boot image touched: `none`.
- Resident already proven: `A90 Linux init 0.11.87 (v3315-gpu-2d-d3-video-semantic-edge-tolerance)`.

## Operator Confirmation

The operator visually confirmed the held V3315 Bad Apple GPU-blit frame on the physical panel:

```text
배드애플 보였다 프레임은 정상적으로 나오는거 같았다
```

This satisfies the final D3/rung-② sensory close condition: the GPU textured-quad path presented a recognizable Bad
Apple frame, and the frame appeared normal to the operator.

## Device Evidence Already Collected

No new device action was required for this close report. The close relies on the already committed V3315 live and
replay evidence:

- Source/build report: `NATIVE_INIT_V3315_GPU_2D_D3_VIDEO_SEMANTIC_EDGE_TOLERANCE_SOURCE_BUILD_2026-06-27.md`
- Live validation report: `NATIVE_INIT_V3315_GPU_2D_D3_VIDEO_SEMANTIC_EDGE_TOLERANCE_LIVE_2026-06-27.md`
- Eye-confirm replay report: `NATIVE_INIT_V3315_GPU_2D_D3_VIDEO_EYE_CONFIRM_REPLAY_HELD_2026-06-27.md`
- Max-hold replay report: `NATIVE_INIT_V3315_GPU_2D_D3_VIDEO_EYE_CONFIRM_REPLAY_MAX_HOLD_2026-06-27.md`

Key telemetry from the V3315 D3 proof:

- `gpu.d3.video.result=video-texture-present-pass`
- `gpu.d3.video.presented=60`
- `gpu.d3.video.fps_milli=29655`
- `gpu.d3.video.changed_total=41472000`
- `gpu.d3.video.semantic.sample_count=64`
- `gpu.d3.video.semantic.match_count=64`
- `gpu.d3.video.semantic.exact_match_count=63`
- `gpu.d3.video.semantic.edge_tolerant_match_count=1`
- `gpu.d3.video.semantic.edge_tolerance_radius=1`
- `gpu.d3.video.semantic.mismatch_count=0`
- `gpu.d3.video.semantic.output_other_count=0`
- `gpu.d3.video.present_rc=0`
- `A90P1 END seq=10 cmd=gpu rc=0 errno=0 duration_ms=62265 flags=0x0 status=ok`

Replay evidence repeated the same path with a 60 s hold:

- `gpu.d3.video.result=video-texture-present-pass`
- `gpu.d3.video.presented=60`
- `gpu.d3.video.fps_milli=30005`
- `gpu.d3.video.semantic.match_count=64`
- `gpu.d3.video.semantic.edge_tolerant_match_count=1`
- `gpu.d3.video.semantic.mismatch_count=0`
- `gpu.d3.video.semantic.output_other_count=0`
- Post-replay selftest: `pass=12 warn=1 fail=0`
- Focused dmesg fault filter matched no KGSL/Adreno/GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault
  signature.

## Closure

V3315 closes rung ②. The GPU accelerated the existing demo frame path by sampling/scaling Bad Apple frames through the
A6xx texture pipe and presenting the result through KMS. D0 reference recon, D1 static checker texture, D2 real
Bad Apple frame texture readback, and D3 video-present integration are now all complete, with telemetry and operator
visual confirmation. The next GPU-chain item is the rule-of-three extraction backlog: modularize the common KGSL
submit/fence/buffer layer pulled by triangle, compute, and accelerated 2D consumers.
