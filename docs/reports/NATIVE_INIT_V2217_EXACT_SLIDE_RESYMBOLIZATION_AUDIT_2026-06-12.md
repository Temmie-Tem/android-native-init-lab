# Native Init V2217 Exact Slide Resymbolization Audit

## Decision

- Decision: `v2217-live-resymbolized-ropp-still-ambiguous`
- Exact slide: `0x84ef4`
- Live PC resolved: `60` / `62`
- Live LR resolved: `60` / `62`
- Live LR callsite: `60` / `62`
- ROPP exact unwind accepted: `false`

## Live Register Resymbolization

| Source | Top Symbols |
| --- | --- |
| `ctx_pc` | schedule_preempt_disabled:11, preempt_schedule_notrace:5, iterate_dir:4, switchdev_port_same_parent_id:3, security_sem_free:2, generic_file_open:1, __sched_text_start:1, security_key_permission:1, print_type_u64:1, vsprintf:1, register_switchdev_notifier:1, bitmap_parselist:1 |
| `ctx_lr` | iterate_dir:5, pm_clk_resume:4, perf_trace_core_ctl_set_boost:4, ns_to_timespec:3, security_sem_free:3, swap_readpage:2, user_free_preparse:2, sys_prctl:2, __free_zspage:2, swap_slot_free_notify:2, set_dumpable:1, print_type_u64:1 |

| Index | PID | Comm | PC Symbol | PC Offset | LR Symbol | LR Offset | LR Callsite | LR Prev Insn |
| ---: | ---: | --- | --- | ---: | --- | ---: | --- | --- |
| 0 | 3504 | `a90_bpf_perf_re` | `schedule_preempt_disabled` | `32` | `ns_to_timespec` | `848` | `true` | `bl` |
| 1 | 563 | `init` | `schedule_preempt_disabled` | `32` | `pm_clk_resume` | `20` | `true` | `bl` |
| 2 | 563 | `init` | `switchdev_port_same_parent_id` | `160` | `swap_readpage` | `128` | `true` | `bl` |
| 3 | 563 | `init` | `generic_file_open` | `108` | `set_dumpable` | `68` | `true` | `bl` |
| 4 | 563 | `init` | `__sched_text_start` | `24` | `iterate_dir` | `152` | `true` | `bl` |
| 5 | 563 | `init` | `iterate_dir` | `76` | `iterate_dir` | `72` | `true` | `bl` |
| 6 | 563 | `init` | `iterate_dir` | `128` | `iterate_dir` | `72` | `true` | `bl` |
| 7 | 563 | `init` | `security_key_permission` | `196` | `user_free_preparse` | `84` | `true` | `bl` |
| 8 | 563 | `init` | `print_type_u64` | `152` | `print_type_u64` | `212` | `true` | `bl` |
| 9 | 563 | `init` | `vsprintf` | `140` | `fslog_open_dlog_rmdir` | `192` | `true` | `bl` |
| 10 | 563 | `init` | `iterate_dir` | `76` | `iterate_dir` | `72` | `true` | `bl` |
| 11 | 563 | `init` | `None` | `None` | `None` | `None` | `false` | `out-of-range` |

## ROPP Decode Attempt

- Tested samples: `59`
- Unique samples: `0`
- Ambiguous samples: `58`
- No-match samples: `1`
- Same-function reduced unique samples: `0`
- Candidate min/median/max: `0` / `43496` / `49848`
- Reduced min/median/max: `0` / `0` / `38`
- Reason: saved FP LR decode still needs extra key/stack constraints

| Index | PID | Comm | Context Function | Candidates | Reduced | Encoded LR1 | Encoded LR2 |
| ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| 0 | 3504 | `a90_bpf_perf_re` | `schedule_preempt_disabled` | 34996 | 0 | `0x70f47b79235db92a` | `0x70f47b7922e4185e` |
| 1 | 563 | `init` | `schedule_preempt_disabled` | 45374 | 0 | `0xea3cdf14f449a498` | `0xea3cdf14f4498fa8` |
| 2 | 563 | `init` | `switchdev_port_same_parent_id` | 42364 | 0 | `0x791a7e8739fe36c0` | `0x791a7e8739f678d0` |
| 3 | 563 | `init` | `generic_file_open` | 48530 | 2 | `0x059ca032b3d6f3f5` | `0x059ca032b3d6f2c9` |
| 4 | 563 | `init` | `__sched_text_start` | 46110 | 0 | `0x750c19ac3c791f37` | `0x750c19ac3c791757` |
| 5 | 563 | `init` | `iterate_dir` | 46110 | 0 | `0x7b125c75f716b071` | `0x7b125c75f716b811` |
| 6 | 563 | `init` | `iterate_dir` | 46110 | 0 | `0xc63c02d76cb3e99e` | `0xc63c02d76cb3e1fe` |
| 7 | 563 | `init` | `security_key_permission` | 37034 | 0 | `0x03968c46c7bc0258` | `0x03968c46c7dce0f0` |
| 8 | 563 | `init` | `print_type_u64` | 30660 | 0 | `0xcc446e7995ada066` | `0xcc446e7994a76392` |
| 9 | 563 | `init` | `vsprintf` | 43906 | 0 | `0x19ca6cac587e1cf9` | `0x19ca6cac587de359` |
| 10 | 563 | `init` | `iterate_dir` | 43686 | 2 | `0xf9ab446a0ac5f1f1` | `0xf9ab446a0ac609ad` |
| 12 | 563 | `init` | `register_switchdev_notifier` | 38478 | 0 | `0xd080be5a35191e2a` | `0xd080be5a35387346` |

## Interpretation

- V2217 uses the V2216 codeword-matched slide, not V2215's rank-only slide.
- Live `ctx_pc`/`ctx_lr` are now exact symbol+offset observations for this boot.
- Saved FP-chain LR decoding remains unresolved when only pair-XOR and dense callsite constraints are used.
- The next useful constraint is a real ROPP key source, stacktrace decoder behavior, or a narrower same-function live probe.

## Evidence

- V2216 summary: `workspace/private/runs/kernel/v2216-perf-regs-codeword-sample-ring-5s-20260612-053331/summary.json`
- System.map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Kernel raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- Private result: `workspace/private/runs/kernel/v2217-exact-slide-resymbolization-audit/result.json`

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`
- partition_or_firmware_write: `false`
