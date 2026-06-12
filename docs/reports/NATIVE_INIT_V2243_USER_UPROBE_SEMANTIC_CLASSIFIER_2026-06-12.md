# Native Init V2243 User Uprobe Semantic Classifier

Date: `2026-06-12`

## Identity

| Field | Value |
| --- | --- |
| Run ID | `V2243` |
| Track | `T1 kernel observation` |
| Device baseline | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Runner | `workspace/public/src/scripts/revalidation/a90_kernel_v2243_user_uprobe_semantic_classifier.py` |
| Private evidence | `workspace/private/runs/kernel/v2243-user-uprobe-semantic-classifier-20260612-113113/` |
| Device flash | no |
| Wi-Fi scan/connect/DHCP/ping | no |

## Track Selection

T1 remains the highest meaningful track. V2242 proved helper-owned `a90*`
static offsets land in executable user-ELF code and banked bounded private
instruction windows. The next bounded unit was to convert those private windows
into a public semantic summary: event role, target instruction class, and
role/instruction alignment.

No track transition occurred. T2 WLAN work was not selected because this unit is
host-only and improves the existing kernel/user observation interpretation
stack.

## Question

Can V2242's private stripped-ELF instruction context be reduced to public,
metadata-only semantic classes without publishing raw bytes or raw disassembly?

## Method

The runner:

1. read V2242's private instruction context JSON;
2. located each target offset in its bounded disassembly window;
3. classified target instruction shape into coarse classes such as `call`,
   `frame_prologue`, `conditional_branch`, `compare`, `load`, `store`, and
   `address_or_alu`;
4. classified each event name into coarse roles such as `entry`, `call_edge`,
   `return_or_result`, `protocol_edge`, `state_edge`, `wait_edge`, and
   `signal_edge`;
5. emitted public metadata only, while writing raw instruction-line triples to
   private evidence.

Inputs:

- `workspace/private/runs/kernel/v2242-user-elf-offset-context-20260612-112444/summary.json`
- `workspace/private/runs/kernel/v2242-user-elf-offset-context-20260612-112444/private_instruction_context.json`

Validation commands:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/a90_kernel_v2243_user_uprobe_semantic_classifier.py
python3 workspace/public/src/scripts/revalidation/a90_kernel_v2243_user_uprobe_semantic_classifier.py --out-dir workspace/private/runs/kernel/v2243-user-uprobe-semantic-classifier-20260612-113113
```

## Result

Decision:

```text
v2243-user-uprobe-semantic-classifier-pass
```

Coverage:

| Metric | Value |
| --- | ---: |
| classified entries | `107` |
| target found count | `107` |
| missing target count | `0` |
| key events | `11` |
| key low-confidence count | `0` |

Confidence distribution:

| Confidence | Count |
| --- | ---: |
| `high` | `56` |
| `medium` | `35` |
| `low` | `16` |

The 16 low-confidence rows are non-key context markers that still need manual
private-context interpretation if they become important. No key event fell into
the low-confidence bucket.

Instruction class distribution:

| Instruction class | Count |
| --- | ---: |
| `address_or_alu` | `34` |
| `call` | `30` |
| `conditional_branch` | `17` |
| `load` | `9` |
| `frame_prologue` | `7` |
| `compare` | `5` |
| `other` | `3` |
| `store` | `2` |

Alignment distribution:

| Alignment | Count |
| --- | ---: |
| `marker_edge` | `31` |
| `aligned_post_call` | `24` |
| `aligned_call_site` | `23` |
| `needs_manual_context` | `16` |
| `aligned_entry_prologue` | `6` |
| `plausible_path_marker` | `4` |
| `aligned_branch_or_compare` | `3` |

Key event semantic map:

| Object | Event | Role | Instruction class | Previous | Next | Alignment | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `a90cnss` | `wlfw_service_request` | `protocol_edge` | `address_or_alu` | `call` | `frame_prologue` | `marker_edge` | `medium` |
| `a90cnss` | `wlfw_worker_done_signal` | `signal_edge` | `address_or_alu` | `branch` | `other` | `marker_edge` | `medium` |
| `a90cnss` | `wlfw_worker_post_done_wait` | `wait_edge` | `call` | `other` | `load` | `marker_edge` | `medium` |
| `a90cnss` | `wlfw_start` | `entry` | `frame_prologue` | `branch` | `store` | `aligned_entry_prologue` | `high` |
| `a90cnss` | `wlfw_cap_qmi` | `protocol_edge` | `call` | `store` | `load` | `marker_edge` | `medium` |
| `a90cnss` | `wlfw_bdf_entry` | `entry` | `frame_prologue` | `call` | `store` | `aligned_entry_prologue` | `high` |
| `a90cnss` | `wlfw_bdf_send_ret` | `return_or_result` | `conditional_branch` | `call` | `load` | `aligned_post_call` | `high` |
| `a90cnss` | `wlfw_bdf_result_log` | `log_edge` | `load` | `address_or_alu` | `address_or_alu` | `marker_edge` | `medium` |
| `a90libqmi` | `libqmi_loop_client_init_ret` | `return_or_result` | `compare` | `call` | `branch` | `aligned_post_call` | `high` |
| `a90pmsrv` | `pm_server_register_entry` | `entry` | `frame_prologue` | `call` | `store` | `aligned_entry_prologue` | `high` |
| `a90pmsrv` | `pm_service_main_supported_list_init` | `state_edge` | `store` | `address_or_alu` | `store` | `marker_edge` | `medium` |

Private semantic instruction lines:

| Field | Value |
| --- | --- |
| Path | `workspace/private/runs/kernel/v2243-user-uprobe-semantic-classifier-20260612-113113/private_semantic_instruction_lines.json` |
| Entries | `107` |

The private file contains raw stripped-ELF instruction lines. It is not
committed and must not be copied into public reports.

## Interpretation

V2243 turns V2242's private context into a reusable public contract:

- all 107 observed helper offsets resolve to a target instruction;
- key WLFW/QMI/PM events have at least medium semantic confidence;
- entry events that matter for `wlfw_start`, `wlfw_bdf_entry`, and
  `pm_server_register_entry` align with frame-prologue targets;
- return/result probes for BDF and libqmi align with post-call checks;
- protocol and state markers are intentionally weaker but usable as ordered
  marker edges in timelines.

This does not replace private disassembly for deep reverse engineering. It only
prevents public reports from carrying raw proprietary code while preserving a
defensible event-role summary.

## Decision

Use V2243 semantic rows when merging helper-owned `a90*` events with kernel
tracepoint or exact-slide evidence:

1. use `alignment`/`confidence` to distinguish hard call/entry evidence from
   marker-only events;
2. keep `needs_manual_context` non-key rows out of strong conclusions unless
   rechecked in private context;
3. do not publish raw instruction bytes or raw disassembly lines;
4. keep the kernel exact-slide path separate from user-ELF semantic classes.

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
