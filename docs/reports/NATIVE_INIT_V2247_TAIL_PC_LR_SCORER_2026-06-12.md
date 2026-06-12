# Native Init V2247 Tail PC/LR Scorer (2026-06-12)

## Scope

Host-only analysis layer for future post-FWREADY tail captures. It maps a
per-boot exact-slide perf regs/codeword summary onto the V2246 source-backed
firmware_class/qcacld-HDD target whitelist. No device I/O, no flash, no BPF
attach, no tracefs write, no Wi-Fi scan/connect, no network route change, and no
private raw helper output is published here.

Inputs:

- `workspace/private/runs/kernel/v2216-perf-regs-codeword-sample-ring-5s-20260612-053331/summary.json`
- `workspace/private/runs/kernel/v2246-post-fwready-tail-symbol-source-map-20260612-115530/summary.json`

Generated private summary:

- `workspace/private/runs/kernel/v2247-tail-pc-lr-scorer-20260612-115952/summary.json`
- `workspace/private/runs/kernel/v2247-tail-pc-lr-scorer-20260612-115952/tail_pc_lr_score.json`

## Result

Decision: `v2247-tail-pc-lr-scorer-pass`.

The scorer accepted the V2216 per-boot exact codeword slide and mapped `ctx_pc`,
`ctx_lr`, and `ctx_lr-4` against the V2246 target whitelist.

| Metric | Value |
| --- | ---: |
| Exact slide accepted | `true` |
| Exact slide | `0x84ef4` |
| PC codeword match | `62/62` |
| LR-4 codeword match | `60/60` |
| LR codeword match | `60/60` |
| Target symbols | `7` |
| Negative-control samples scored | `62` |
| Tail target hits in negative control | `0` |

## Target Set

The scorer uses these V2246 source-backed targets:

- `_request_firmware`
- `request_firmware`
- `qdf_file_read`
- `qdf_ini_parse`
- `cfg_parse`
- `hdd_context_create`
- `wlan_hdd_pld_probe`

## Interpretation

The default V2216 capture is a generic CPU-clock sample, not a post-FWREADY tail
capture. Zero hits against the V2246 tail whitelist is therefore a useful
negative-control check: the scorer does not trivially classify unrelated exact
slide samples as the qcacld/HDD tail.

The next live unit can now run a tail-window perf regs/codeword capture and feed
its summary to this scorer. Nonzero hits in the firmware_class/qdf/cfg/HDD target
set would prove post-FWREADY tail code-path identity with per-boot exact-slide
symbolization.

## Safety

- Host-only parser.
- No device boot, flash, BPF attach, tracefs mutation, Wi-Fi scan/connect, or
  network change.
- Private per-sample scoring stays under `workspace/private/**`.
