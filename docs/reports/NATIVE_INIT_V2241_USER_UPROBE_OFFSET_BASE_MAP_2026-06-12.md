# Native Init V2241 User Uprobe Offset/Base Map

Date: `2026-06-12`

## Identity

| Field | Value |
| --- | --- |
| Run ID | `V2241` |
| Track | `T1 kernel observation` |
| Device baseline | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Runner | `workspace/public/src/scripts/revalidation/a90_kernel_v2241_user_uprobe_offset_base_map.py` |
| Private evidence | `workspace/private/runs/kernel/v2241-user-uprobe-offset-base-map-20260612-111447/` |
| Device flash | no |
| Wi-Fi scan/connect/DHCP/ping | no |

## Track Selection

T1 remains the highest meaningful track. V2240 closed the kernel/user address
boundary: helper-owned `a90*` `__probe_ip` values are user-space addresses and
must not be symbolized with the kernel exact-slide/System.map path.

The next bounded T1 unit was therefore to build the missing user-space identity
layer: join runtime `a90*` probe IPs from existing boot-window parser summaries
with the static uprobe offsets embedded in `a90_android_execns_probe.c`, then
check whether each run/object produces one consistent page-aligned load bias.

No track transition occurred. T2 WLAN work was not selected because this unit is
host-only and directly strengthens the observer interpretation stack.

## Question

Can the existing `a90*` runtime probe IPs be mapped back to their static
user-space uprobe offsets and per-run load biases without new device capture?

## Method

The runner performed host-only postprocessing:

1. parsed static uprobe offset tables from
   `workspace/public/src/native-init/helpers/a90_android_execns_probe.c`;
2. extracted first-hit `a90cnss`, `a90libqmi`, and `a90pmsrv` runtime probe IPs
   from V2229, V2231, and V2233 parser summaries;
3. computed `load_bias = runtime_probe_ip - static_uprobe_offset`;
4. required all matched events for each `(run, object)` to share exactly one
   page-aligned load bias;
5. recorded available stripped user ELF metadata for future disassembly-level
   work.

Inputs:

- `workspace/private/runs/kernel/v2229-live-20260612-080114/parser/summary.json`
- `workspace/private/runs/kernel/v2231-live-20260612-081302/parser/summary.json`
- `workspace/private/runs/kernel/v2233-live-20260612-083738/parser/summary.json`
- `workspace/private/runs/kernel/v2240-codepath-identity-boundary-20260612-110740/summary.json`
- `workspace/public/src/native-init/helpers/a90_android_execns_probe.c`

Validation commands:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/a90_kernel_v2241_user_uprobe_offset_base_map.py
python3 workspace/public/src/scripts/revalidation/a90_kernel_v2241_user_uprobe_offset_base_map.py
```

## Result

Decision:

```text
v2241-user-uprobe-offset-base-map-pass
```

Static spec counts parsed from helper source:

| Group | Static specs |
| --- | ---: |
| `a90cnss` | `141` |
| `a90libqmi` | `21` |
| `a90pmsrv` | `46` |

Runtime probe counts from V2229/V2231/V2233 parser summaries:

| Group | Runtime samples |
| --- | ---: |
| `a90cnss` | `228` |
| `a90libqmi` | `57` |
| `a90pmsrv` | `39` |

Join quality:

| Metric | Value |
| --- | ---: |
| matched observations | `321` |
| missing static specs | `0` |
| parser alias duplicates | `3` |
| `(run, object)` bias groups | `9` |

The three alias duplicates are the same `pm_server_register_entry` hit emitted
once through a legacy `a90cnss`/`uprobe` surface and once through the canonical
`a90pmsrv`/`pm_server_uprobe` surface. The canonical rows are matched; the
duplicates are excluded from missing-spec accounting.

Per-run load-bias map:

| Run | Object | Matched events | Unique biases | Load bias | Page aligned |
| --- | --- | ---: | ---: | ---: | --- |
| `V2229` | `a90cnss` | `75` | `1` | `0x5556972000` | yes |
| `V2229` | `a90libqmi` | `19` | `1` | `0x7fa6908000` | yes |
| `V2229` | `a90pmsrv` | `13` | `1` | `0x5573b84000` | yes |
| `V2231` | `a90cnss` | `75` | `1` | `0x556fe17000` | yes |
| `V2231` | `a90libqmi` | `19` | `1` | `0x7fb3c9c000` | yes |
| `V2231` | `a90pmsrv` | `13` | `1` | `0x5582985000` | yes |
| `V2233` | `a90cnss` | `75` | `1` | `0x55707ea000` | yes |
| `V2233` | `a90libqmi` | `19` | `1` | `0x7f81e2b000` | yes |
| `V2233` | `a90pmsrv` | `13` | `1` | `0x557e75c000` | yes |

Available stripped user ELFs:

| Object | Evidence |
| --- | --- |
| `a90cnss` | `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon` |
| `a90libqmi` | `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmi_cci.so` |
| `a90pmsrv` | `tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source/bin/pm-service` |

All three are AArch64 stripped dynamic ELFs. They are sufficient for
offset/disassembly verification but not source-level symbol names.

## Interpretation

V2241 confirms the correct user-space identity model:

- static uprobe offsets embedded in the helper match runtime probe IPs exactly;
- every mapped `(run, object)` produces one page-aligned load bias;
- the V2240 relative offset signatures are not just stable fingerprints, but
  recoverable `(load_bias + static_offset)` identities.

This closes the immediate post-V2240 gap. Future `a90*` code-path identity should
use the helper source offset table plus per-run load bias. Kernel exact-slide
symbolization remains separate and should only be used for kernel canonical
addresses.

## Decision

Use this contract for future `a90*` interpretation:

1. parse static offsets from `a90_android_execns_probe.c`;
2. compute per-run user-space load bias from observed `__probe_ip`;
3. require one page-aligned load bias per `(run, object)`;
4. use stripped ELF disassembly around static offsets when finer instruction
   context is needed;
5. do not use kernel System.map/KASLR slide for `a90*` user-space records.

## Safety

- `host_only`: true.
- `device_io`: false.
- `bpf_attach`: false.
- `tracefs_control_write`: false.
- `probe_write_user_executed`: false.
- `wifi_scan_connect`: false.
- `network_route_change`: false.
- `flash_reboot`: false.
- `partition_write`: false.
- public output contains only metadata and summary values; private raw artifacts
  remain under `workspace/private/`.
