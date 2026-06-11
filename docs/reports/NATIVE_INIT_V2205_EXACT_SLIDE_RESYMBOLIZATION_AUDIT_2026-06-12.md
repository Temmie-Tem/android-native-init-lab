# Native Init V2205 Exact-Slide Resymbolization Audit

## Decision

- Decision: `v2205-fops-slide-not-universal-text-slide`
- Reason: V2204 fops slide maps clean rodata anchors, but maps existing stack/timer text pointers to semantically implausible symbols.
- V2204 fops/object slide: `0x8179c`
- V2204 sources: `fd0_fop:null_fops, fd1_fop:zero_fops`

## Interpretation

- V2204 remains valid as a clean object/rodata anchor: `/dev/null` and `/dev/zero` f_op pointers agree.
- V2205 blocks promoting that value to a universal text-stack symbolization slide.
- Existing raw text-like values still need a text-side anchor or CFP/JOPP/ROPP decode layer before assigning final function names.

## V2195 Stack Under V2204 Slide

| Index | Runtime IP | Static Address | Symbol | Offset | Schedule-like |
| --- | --- | --- | --- | --- | --- |
| 0 | `0xffffff8009a42334` | `0xffffff80099c0b98` | `netdev_bits` | `240` | `false` |
| 1 | `0xffffff8009a42334` | `0xffffff80099c0b98` | `netdev_bits` | `240` | `false` |
| 2 | `0xffffff8009a429d8` | `0xffffff80099c123c` | `ip6_compressed_string` | `100` | `false` |
| 3 | `0xffffff800819ad8c` | `0xffffff80081195f0` | `pull_dl_task` | `424` | `false` |
| 4 | `0xffffff800819adf0` | `0xffffff8008119654` | `pull_dl_task` | `524` | `false` |
| 5 | `0xffffff80081131f4` | `0xffffff8008091a58` | `cpu_enable_trap_ctr_access` | `2240` | `false` |

## V2202 Timer Rows Under V2204 Slide

| Rank | Comm | Count | Runtime Function | Static Symbol | Offset | Timer-like |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `a90_bpf_timer_o` | 1396 | `0xffffff80083108fc` | `compat_sys_pwritev` | `8` | `false` |
| 1 | `rcu_preempt` | 152 | `0xffffff80081db824` | `trace_event_raw_event_hrtimer_start` | `32` | `true` |
| 2 | `kworker/7:1` | 139 | `0xffffff80081510c4` | `compat_SyS_setrlimit` | `64` | `false` |
| 3 | `init` | 7 | `0xffffff8008a1e884` | `__dev_pm_qos_flags` | `56` | `false` |
| 4 | `swapper/0` | 4 | `0xffffff800815b4d4` | `sys_mq_notify` | `96` | `false` |
| 5 | `crtc_commit:133` | 4 | `0xffffff800883ed5c` | `drm_property_create_object` | `1216` | `false` |
| 6 | `crtc_commit:133` | 4 | `0xffffff800889adf4` | `_sde_crtc_misr_setup` | `568` | `false` |
| 7 | `a90_bpf_timer_o` | 3 | `0xffffff8008291e3c` | `adjust_managed_page_count` | `192` | `false` |
| 8 | `kworker/2:1` | 2 | `0xffffff80085a42ac` | `trace_event_raw_event_block_bio_bounce` | `0` | `false` |
| 9 | `mmcqd/0` | 2 | `0xffffff80093508a4` | `mmc_cmdq_rq_timed_out` | `2272` | `false` |
| 10 | `mmcqd/0` | 2 | `0xffffff800935095c` | `mmc_cmdq_rq_timed_out` | `2456` | `false` |

## Legacy Context

- V2197 top text-candidate delta from V2204: `0x26c0`
- V2203 decision: `v2203-row-matcher-no-exact-slide`
- V2203 reason: best candidate still has hard row/object conflicts

## Next

- Build a text-side anchor, preferably by extending the file-ops path to read known fops member function pointers.
- Treat fops object addresses and stack/timer text addresses as separate interpretation layers until that anchor converges.

## Evidence

- system_map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- v2195_stack_report: `docs/reports/NATIVE_INIT_V2195_STACKMAP_DUMP_LIVE_2026-06-11.md`
- v2197_symbolization: `workspace/private/runs/kernel/v2197-stock-kallsyms/symbolization.json`
- v2202_summary: `workspace/private/runs/kernel/v2202-timer-object-histogram-20260612-010308/summary.json`
- v2203_result: `workspace/private/runs/kernel/v2203-timer-row-source-matcher/result.json`
- v2204_summary: `workspace/private/runs/kernel/v2204-file-ops-anchor-20260612-012852/summary.json`
