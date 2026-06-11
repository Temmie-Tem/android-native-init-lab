# Native Init V2213 Raw Frame Sample Ring

## Decision

- Decision: `v2213-raw-frame-sample-ring-captured`
- Pass: `true`
- Total samples observed: `629`
- Printed samples parsed: `629`
- Occupied ring slots: `629` / `1024`
- Selftest fail=0: `true`

## Method

- Uses bounded BPF array maps: one stats row plus a 1024-slot sample ring.
- Supports helper-pid mode and `--all-tasks` mode; no unbounded kernel storage is used.
- Samples `thread.cpu_context.{fp,sp,pc}` plus raw `fp/sp` slots with `bpf_probe_read` only.
- Does not use `probe_write_user`, cgroup attach, Wi-Fi, flash, reboot, or partition/firmware writes.

## Metrics

- Unique comms: `19`
- Unique pids: `15`
- Walkable `fp_slot_next`: `4`
- Walkable `fp2_slot_next`: `3`
- Raw LR nonzero: `629`
- Raw LR in kernel text: `0`
- Raw LR kernel VA outside text: `626`
- Thread PC in kernel text: `629`

| Field | Unique Count | Preview |
| --- | ---: | --- |
| `thread_pc` | 1 | 0xffffff8008106428 |
| `fp_slot_raw_lr` | 5 | 0x07ceddb5432dbaf7, 0x291afa2f431c2ba1, 0xffffffc080d40f40, 0xffffffc178b00f80, 0xffffffc17fb63000 |
| `fp_slot_next` | 3 | 0x00000000deaddead, 0xffffff800bc1bcd0, 0xffffff800bc23cd0 |
| `fp2_slot_raw_lr` | 2 | 0x07ceddb5429fb447, 0x291afa2f42ae2511 |
| `sp_slot8` | 5 | 0x07ceddb5432dbaf7, 0x291afa2f431c2ba1, 0xffffffc080d40f40, 0xffffffc178b00f80, 0xffffffc17fb63000 |

## Convergence

- Ring saturated: `false`
- Hint: ring not saturated; longer duration can still add information

## Staged Comparison

| Run | Total | Occupied | Printed | Saturated | Unique comms | Unique pids | Unique `thread_pc` | Unique `fp_slot_raw_lr` | Unique `fp_slot_next` | Raw LR in text |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `250ms-all-task` | 629 | 629 | 629 | false | 19 | 15 | 1 | 5 | 3 | 0 |
| `5s-all-task` | 12429 | 1024 | 512 | true | 16 | 13 | 1 | 5 | 3 | 0 |

The staged result down-ranks pure runtime extension as a fix.  The 5s run
observed about 20x more sched_switch events than the 250ms run, but the relevant
unique counts did not grow: `thread_pc` stayed at one value, `fp_slot_raw_lr`
stayed at five values, `fp_slot_next` stayed at three values, and no raw LR fell
inside kernel text.

Interpretation: longer sampling is useful for confidence, but not sufficient to
recover the V2195 stack frames from this tracepoint shape.  The next useful
change is structural: sample a tracepoint/helper path that exposes a
non-current/sleeping task pointer, or capture a true register frame context
instead of `current->thread.cpu_context` at `sched_switch`.

## Safety

- read_only_bpf: `true`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`
- partition_or_firmware_write: `false`

## Evidence

- Private run: `workspace/private/runs/kernel/v2213-raw-frame-sample-ring-250ms-20260612-040853`
- Comparison run: `workspace/private/runs/kernel/v2213-raw-frame-sample-ring-20260612-040745`
- Helper SHA-256: `8727a91bb632b2efdf5472673ba3c48ba292e67b84367c07c8bafc2f10e5aa0f`
