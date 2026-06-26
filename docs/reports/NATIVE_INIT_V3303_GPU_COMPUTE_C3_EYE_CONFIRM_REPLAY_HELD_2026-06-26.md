# Native Init V3303 GPU Compute C3 Eye-Confirm Replay Held

## Summary

- Cycle: `V3303`
- Track: GPU visible compute demo C3, operator eye-confirm replay.
- Decision: `v3303-c3-eye-confirm-replay-held-device-pass`
- Result: PASS for replaying the existing V3303 compute pattern to KMS and holding it for 60 s.
- Device flash: `no`.
- Boot image touched: `none`.
- Visual close: pending operator statement that the held pattern was visible on the panel.

## Preconditions

- Bridge recovered from the earlier USB absence and reported `connected-no-immediate-error`.
- Serial endpoint: `/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00` -> `/dev/ttyACM0`.
- Resident version:
  - `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`
  - `A90P1 END seq=9 cmd=version rc=0 errno=0 duration_ms=0 flags=0x0 status=ok`
- Pre-replay selftest: `pass=12 warn=1 fail=0`.

## Replay Command

The replay used the existing V3303 command; no rebuild was required:

```text
cmdv1 hide
cmdv1 gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 60000 --materialize-devnode
```

Key results:

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
- `gpu.c3.kms.total_elapsed_ms=60041`
- `A90P1 END seq=12 cmd=gpu rc=0 errno=0 duration_ms=60041 flags=0x0 status=ok`

## Post Validation

- Post-replay selftest: `pass=12 warn=1 fail=0`.
- Bridge state after replay: `connected-no-immediate-error`.
- Fault filter over bridge logs matched no KGSL/GMU/ringbuffer/CP/GPU/IOMMU/page-fault pattern.
- Safety markers from the live run:
  - `gpu.c3.kms.power_write_attempted=0`
  - `gpu.c3.kms.proprietary_blob_attempted=0`
  - `gpu.c3.kms.kms_blit_attempted=1`
  - `gpu.c3.kms.zero_copy_attempted=0`
  - `gpu.c3.kms.scaled_plane_attempted=0`

## Conclusion

The existing V3303 C3 path was successfully replayed after USB visibility returned. The device proved compute output,
KMS presentation, and a 60 s hold. The remaining close condition is operator eye confirmation that the held compute
pattern was visible on the panel.
