# Native Init V3303 GPU Compute C3 KMS Live Validation

## Summary

- Cycle: `V3303`
- Track: GPU visible compute demo C3, C2 UAV pattern expanded to KMS.
- Decision: `v3303-gpu-compute-c3-kms-live-device-presented-held-pass`
- Result: PASS for device-side compute readback, KMS present, and 30 s hold.
- Visual close: pending operator eye confirmation of the held panel pattern.
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3303_gpu_compute_c3_kms_probe.img`
- Boot SHA256: `0a041e834cedae3b54bea5c1b4fb70b4be133156e8c9317d8f6c30b304c01e20`
- Init: `A90 Linux init 0.11.77 (v3303-gpu-compute-c3-kms-probe)`

## Flash Gate

- Rollback images verified before flash:
  - `v2321`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `v2237`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `v48`: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
  - TWRP recovery: `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`
- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`
- Helper readback: boot prefix SHA matched `0a041e834cedae3b54bea5c1b4fb70b4be133156e8c9317d8f6c30b304c01e20`.
- Post-flash helper check: `version` and `status` returned `rc=0`, `selftest fail=0`.

## Live Command

The serial line had intermittent unsolicited `AT` bytes, so the live command was sent through the same bridge after
clearing the current shell line with Ctrl-U and writing the full `cmdv1` line in one socket write.

Command:

```text
cmdv1 gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode
```

Key results:

- `gpu.c3.kms.materialize_rc=0`
- `gpu.c2.compute.result=pattern-readback-pass`
- `gpu.c2.compute.snapshot_write_rc=0`
- `gpu.c2.compute.snapshot_write_bytes=65536`
- `gpu.c2.compute.expected_match_count=16384`
- `gpu.c2.compute.mismatch_count=0`
- `gpu.c2.compute.pass=1`
- `gpu.c3.kms.snapshot_read_rc=0`
- `gpu.c3.kms.snapshot_read_bytes=65536`
- `gpu.c3.kms.snapshot_expected_match_count=16384`
- `gpu.c3.kms.snapshot_mismatch_count=0`
- `gpu.c3.kms.fb_width=1080`
- `gpu.c3.kms.fb_height=2400`
- `gpu.c3.kms.fb_stride=4352`
- `gpu.c3.kms.blit_rect=92,752,896,896`
- `gpu.c3.kms.blit_scale=7`
- `gpu.c3.kms.present_rc=0`
- `gpu.c3.kms.result=compute-pattern-presented`
- `gpu.c3.vis.hold_elapsed_ms=30000`
- `gpu.c3.vis.result=compute-pattern-presented-held`
- `A90P1 END seq=6 cmd=gpu rc=0 errno=0 duration_ms=30161 flags=0x0 status=ok`

## Post Validation

- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Bridge capture fault filter for KGSL/GMU/ringbuffer/CP/GPU/IOMMU/page-fault patterns: no matches.
- Safety markers from the live run:
  - `gpu.c3.kms.power_write_attempted=0`
  - `gpu.c3.kms.proprietary_blob_attempted=0`
  - `gpu.c3.kms.kms_blit_attempted=1`
  - `gpu.c3.kms.zero_copy_attempted=0`
  - `gpu.c3.kms.scaled_plane_attempted=0`

## Conclusion

V3303 proves the device-side C3 path: verified GPU compute output is written to a bounded snapshot, read back,
expanded into the KMS dumb framebuffer, presented on `/dev/dri/card0`, and held for 30 seconds. The compute-demo
close still needs operator eye confirmation that the held pattern was visible on the panel.
