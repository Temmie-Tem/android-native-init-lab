# Native Init V3320 GPU M3 Monitor Extraction Live Validation

## Summary

- Cycle: `V3320`
- Track: GPU rung 3, M3 shared KGSL 2D present extraction.
- Result: PASS
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3320_gpu_m3_monitor_extraction.img`
- Boot SHA256: `dd2f4fa31b81340ad35477cb0d23655b9b837887272a4224926311e04ef43ea2`
- Init after flash: `A90 Linux init 0.11.91 (v3320-gpu-m3-monitor-extraction)`
- Device identifiers, serial paths, network addresses, storage UUIDs, and raw logs are intentionally omitted.

## Flash Gate

- Rollback `v2321` image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Fallback `v2237` image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Fallback `v48` image SHA256 matched `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- Pre-flash device was V3319 with selftest `pass=12 warn=1 fail=0`.
- Flash was performed only through `native_init_flash.py`; remote image SHA and boot readback SHA both matched the V3320 artifact.
- Post-flash native-init verify passed with version/status rc=0.

## M3 Probe

Command:

```text
gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 5000 --materialize-devnode
```

Key telemetry:

- `gpu.m3.extract.layer=gpu_2d_present_v1`
- `gpu.m3.extract.shared_core=bo-map,sync-to-gpu,submit-wait,linear-readback,kms-copy`
- `gpu.m3.extract.kgsl_submit_attempted=1`
- `gpu.m3.extract.kms_present_attempted=1`
- `gpu.m3.extract.power_write_attempted=0`
- `gpu.m3.extract.proprietary_blob_attempted=0`
- M2 delegate result: `gpu.m2.graph.result=monitor-live-graph-pass`
- Presented frames: `gpu.m2.graph.presented=12`
- KMS present: `gpu.m2.graph.present_rc=0`
- Semantic validation: `sample_count=64`, `match_count=64`, `mismatch_count=0`, `output_other_count=0`
- Result: `gpu.m3.extract.result=shared-2d-present-monitor-pass`

## D3 Regression

Command:

```text
gpu d3-video-texture-present-probe --preset badapple --start-frame 515 --frames 3 --timeout-ms 30000 --hold-ms 0 --materialize-devnode
```

Key telemetry:

- `gpu.d3.video.extraction_layer=gpu_2d_present_v1`
- `gpu.d3.video.result=video-texture-present-pass`
- `gpu.d3.video.presented=3`
- `gpu.d3.video.present_rc=0`
- Semantic validation: `sample_count=64`, `match_count=64`, `mismatch_count=0`, `output_other_count=0`
- Operator visual note for the Bad Apple path: visible, with frames appearing normal.

## Health

- Post-probe selftest stayed `pass=12 warn=1 fail=0`.
- A non-gating `hide` request printed `menu: hide requested` but returned without an `A90P1 END` marker; it did not affect the M3/D3 validation commands.

## Status

M3 extraction telemetry and the focused D3 Bad Apple regression passed. The remaining human-facing close item for the full ③ monitor rung is an explicit operator eye-confirmation of the held live monitor panel, if required before promoting the rung from telemetry-pass to eye-confirmed.
