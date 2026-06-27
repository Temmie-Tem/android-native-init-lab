# Native Init V3321 GPU M3 Hold Timeout Budget Live Validation

## Summary

- Cycle: `V3321`
- Track: GPU rung 3, M3 visual hold timeout-budget fix.
- Result: PASS
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3321_gpu_m3_hold_timeout_budget.img`
- Boot SHA256: `48050046e743694d6e74ed6123b49f87d5d2dd0f87a44bd14e3d548431ca9a49`
- Init after flash: `A90 Linux init 0.11.92 (v3321-gpu-m3-hold-timeout-budget)`
- Device identifiers, serial paths, network addresses, storage UUIDs, and raw logs are intentionally omitted.

## Flash Gate

- Rollback `v2321` image SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Fallback `v2237` image SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Fallback `v48` image SHA256 matched `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- TWRP recovery image SHA256 matched `b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`.
- Pre-flash device was V3320 with selftest `pass=12 warn=1 fail=0`.
- Flash was performed only through `native_init_flash.py`; remote image SHA and boot readback SHA both matched the V3321 artifact.
- Post-flash native-init verify passed with version/status rc=0.

## M3 Hold Probe

Command:

```text
gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 60000 --materialize-devnode
```

Key telemetry:

- Initial attempt was rejected as busy because the auto menu was active; `hide` returned rc=0 and the same probe was rerun.
- `gpu.m3.extract.layer=gpu_2d_present_v1`
- `gpu.m2.graph.timeout_ms=60000`
- `gpu.m2.graph.hold_ms=60000`
- `gpu.m2.graph.parent_timeout_ms=125000`
- `gpu.m2.graph.timeout_split=render-plus-visual-hold`
- `gpu.m2.graph.timed_out=0`
- `gpu.m2.graph.child_killed=0`
- M2 delegate result: `gpu.m2.graph.result=monitor-live-graph-pass`
- Presented frames: `gpu.m2.graph.presented=12`
- KMS present: `gpu.m2.graph.present_rc=0`
- Graph pixels: `gpu.m2.graph.graph_pixels_set=2733`
- CPU/cluster topology: `cpu.count=8`, `cluster.count=3`
- Semantic validation: `sample_count=64`, `match_count=64`, `mismatch_count=0`, `output_other_count=0`
- Result: `gpu.m3.extract.result=shared-2d-present-monitor-pass`
- Command duration: `62502ms`

## Operator Eye-Confirmation Replay

No new flash was performed. The already-flashed V3321 resident was rechecked first:

- Version: `A90 Linux init 0.11.92 (v3321-gpu-m3-hold-timeout-budget)`
- Pre-replay selftest: `pass=12 warn=1 fail=0`

First replay:

```text
hide
gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 60000 --materialize-devnode
```

- The operator reported that graph-like content was visible, but the automatic HUD may have interfered with the visual hold.
- Telemetry still passed: `presented=12`, `present_rc=0`, `timed_out=0`, `child_killed=0`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`, `gpu.m3.extract.result=shared-2d-present-monitor-pass`.
- Follow-up selftest: `pass=12 warn=1 fail=0`.

Second replay used the stronger foreground-display setup:

```text
stophud
gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 60000 --materialize-devnode
```

- `stophud` reported `autohud: stopped`.
- Telemetry passed: `presented=12`, `present_rc=0`, `timed_out=0`, `child_killed=0`, `graph_pixels_set=2720`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`, `gpu.m3.extract.result=shared-2d-present-monitor-pass`.
- Command duration: `63588ms`.
- Follow-up selftest: `pass=12 warn=1 fail=0`.
- Operator eye-confirmation: "보인다 유지되는거 같다".

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

## Health

- Post-probe selftest stayed `pass=12 warn=1 fail=0`.

## Status

V3321 fixes the V3320 60-second hold collision by separating the render timeout from the visual hold budget. The no-flash `stophud` replay also closes the human-facing gate: the held live monitor panel was visible and stayed on screen according to operator confirmation. The full ③ monitor rung is now telemetry-pass and eye-confirmed.
