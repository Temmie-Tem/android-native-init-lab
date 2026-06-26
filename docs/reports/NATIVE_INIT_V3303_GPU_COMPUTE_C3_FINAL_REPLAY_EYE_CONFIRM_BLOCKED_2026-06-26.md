# Native Init V3303 GPU Compute C3 Final Replay Eye-Confirm Blocked

## Summary

- Cycle: `V3303`
- Track: GPU visible compute demo C3, final replay for operator eye confirmation.
- Decision: `v3303-c3-final-replay-eye-confirm-blocked`
- Result: DEVICE PASS, blocked only on operator visual statement.
- Device flash: `no`.
- Boot image touched: `none`.
- Resident: `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`.

## Final Replay

The existing V3303 image was used; no rebuild or flash was required.

```text
cmdv1 version
cmdv1 selftest verbose
cmdv1 hide
cmdv1 gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 60000 --materialize-devnode
```

Key results:

- `version rc=0`
- Pre-replay selftest: `pass=12 warn=1 fail=0`
- `gpu.c2.compute.snapshot_write_bytes=65536`
- `gpu.c2.compute.expected_match_count=16384`
- `gpu.c2.compute.mismatch_count=0`
- `gpu.c2.compute.pass=1`
- `gpu.c2.compute.total_elapsed_ms=15`
- `gpu.c3.kms.snapshot_expected_match_count=16384`
- `gpu.c3.kms.snapshot_mismatch_count=0`
- `gpu.c3.kms.blit_rect=92,752,896,896`
- `gpu.c3.kms.blit_scale=7`
- `gpu.c3.kms.present_rc=0`
- `gpu.c3.kms.result=compute-pattern-presented`
- `gpu.c3.vis.hold_elapsed_ms=60000`
- `gpu.c3.vis.result=compute-pattern-presented-held`
- `gpu.c3.kms.total_elapsed_ms=60042`
- `A90P1 END seq=17 cmd=gpu rc=0 errno=0 duration_ms=60042 flags=0x0 status=ok`

## Post Validation

- Post-replay selftest: `pass=12 warn=1 fail=0`.
- Final bridge status: `connected-no-immediate-error`.
- Fault filter over bridge logs matched no KGSL/GMU/ringbuffer/CP/GPU/IOMMU/page-fault pattern.
- Safety markers from the C3 command remained:
  - `gpu.c3.kms.power_write_attempted=0`
  - `gpu.c3.kms.proprietary_blob_attempted=0`
  - `gpu.c3.kms.kms_blit_attempted=1`
  - `gpu.c3.kms.zero_copy_attempted=0`
  - `gpu.c3.kms.scaled_plane_attempted=0`

## Blocker

The device-side C3 path is proven and has been replayed with a 60 s hold multiple times. The only remaining close
condition in `GOAL.md` is an operator statement that the held compute pattern was visible on the physical panel. That
statement cannot be produced by local host commands or device telemetry.

When the operator confirms visibility, close C3 in `GOAL.md` as the visible compute-demo completion. If the operator
reports the pattern was not visible, continue from the V3303 replay logs and inspect the KMS/panel presentation path
without rebuilding first.
