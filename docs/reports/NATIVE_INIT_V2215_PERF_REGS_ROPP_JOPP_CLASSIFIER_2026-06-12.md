# Native Init V2215 Perf Regs ROPP/JOPP Classifier

## Decision

- Decision: `v2215-slide-ranked-ropp-ambiguous`
- Host-only: `true`
- Best slide: `0x879f4`
- P0 exact slide accepted: `false`
- Best weighted score: `210`
- P2 exact unwind accepted: `false`

## P0 Slide Classifier

- Runtime samples: PC `80`, LR `80`
- Text range: `0xffffff8008080060` -> `0xffffff8009a03084`
- Best PC function hits: `80` / `80`
- Best LR function hits: `80` / `80`
- Best LR callsite hits: `25` / `80`
- Exact-slide threshold: `40` LR callsite hits
- Exact-slide reason: candidate is useful for ranking, but LR-callsite support is below exact-slide threshold

| Rank | Slide | Score | PC Func | LR Func | LR Callsite | Direct | Springboard | Top Symbols |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `0x879f4` | 210 | 80 | 80 | 25 | 25 | 0 | ip4_addr_string:21, ip4_addr_string_sa:17, perf_trace_sched_process_wait:17, set_freezable:12, cpuset_mem_spread_node:4 |
| 2 | `0x48ba0` | 199 | 79 | 80 | 20 | 20 | 0 | __secondary_switched:39, update_task_pred_demand:17, cpuset_read_s64:13, _raw_spin_lock_irq:12, bpf_prog_realloc:6 |
| 3 | `0x48ba4` | 199 | 79 | 80 | 20 | 20 | 0 | __secondary_switched:39, update_task_pred_demand:17, cpuset_read_s64:13, _raw_spin_lock_irq:12, bpf_prog_realloc:6 |
| 4 | `0xbac58` | 194 | 80 | 78 | 18 | 18 | 0 | perf_trace_cfg80211_cqm_pktloss_notify:21, trace_event_raw_event_cfg80211_pmksa_candidate_notify:17, print_tainted:17, sched_ktime_clock:13, hrtimer_interrupt:5 |
| 5 | `0x879f8` | 190 | 80 | 80 | 15 | 15 | 0 | ip4_addr_string:21, ip4_addr_string_sa:17, perf_trace_sched_process_wait:17, set_freezable:12, cpuset_mem_spread_node:4 |
| 6 | `0x45228` | 188 | 62 | 80 | 23 | 23 | 0 | ropp_enable_backtrace:21, sched_autogroup_exit:17, audit_log_n_hex:12, _raw_spin_lock_irq:10, bpf_int_jit_compile:6 |
| 7 | `0xbac60` | 178 | 80 | 78 | 10 | 10 | 0 | perf_trace_cfg80211_cqm_pktloss_notify:21, trace_event_raw_event_cfg80211_pmksa_candidate_notify:17, print_tainted:17, sched_ktime_clock:13, hrtimer_interrupt:5 |
| 8 | `0x25908` | 177 | 35 | 78 | 32 | 32 | 0 | init_irq_proc:17, tracing_stat_release:12, perf_event_get:4, blk_queue_io_vol_del:4, fscrypt_sdp_get_storage_type:4 |
| 9 | `0x25380` | 176 | 33 | 77 | 33 | 33 | 0 | irq_affinity_hint_proc_show:17, stat_seq_next:12, blk_delay_queue:5, sha224_base_init:4, perf_event_attrs:4 |
| 10 | `0xbac64` | 176 | 80 | 78 | 9 | 9 | 0 | perf_trace_cfg80211_cqm_pktloss_notify:21, trace_event_raw_event_cfg80211_pmksa_candidate_notify:17, print_tainted:17, sched_ktime_clock:13, hrtimer_interrupt:5 |
| 11 | `0x69f88` | 176 | 80 | 80 | 8 | 8 | 0 | _raw_spin_lock_irq:43, account_system_index_time:17, tick_handle_oneshot_broadcast:12, five_process_vm_rw:5, sidtab_search:4 |
| 12 | `0x87aac` | 175 | 80 | 79 | 8 | 8 | 0 | ip6_addr_string:38, perf_trace_sched_process_wait:17, set_freezable:12, smack_sem_associate:5, cpuset_mem_spread_node:4 |

## P1 Generated/Late-Text Discriminator

- No-slide PC categories: `{'post_etext_no_slide': 50, 'core_text_no_slide': 30}`
- No-slide LR categories: `{'post_etext_no_slide': 3, 'core_text_no_slide': 77}`
- No-slide PC nearest symbols: `[('sel_policy_ops', 39), ('elv_completed_request', 2), ('bvec_free', 2), ('task_state_array', 2), ('__put_page', 2), ('proc_pid_status', 2)]`
- No-slide LR nearest symbols: `[('tick_setup_periodic', 17), ('bpf_get_file_flag', 12), ('bounce_end_io_read_isa', 4), ('query_usecase', 3), ('scsi_seq_show', 3), ('__bpf_prog_charge', 3)]`
- Under best slide PC categories: `{'function_range': 76, 'function_and_callsite': 4}`
- Under best slide LR categories: `{'function_range': 55, 'function_and_callsite': 25}`

- Direct `_end_hyperdrive`/post-`_etext` range hits are classified as no-slide artifacts unless the best-slide view still lands there.
- This keeps direct range lookup separate from exact callgraph naming.

## P2 ROPP Saved-LR Decode Audit

- Tested samples: `78`
- Unique decode samples: `0`
- Ambiguous decode samples: `78`
- No-match samples: `0`
- Candidate count min/median/max: `30882` / `37502.0` / `51278`
- Reason: ROPP pair decode remains ambiguous or unmatched under callsite constraints

| Sample | PID | Comm | Candidates | Encoded LR1 | Encoded LR2 |
| ---: | ---: | --- | ---: | --- | --- |
| 0 | 3476 | `a90_bpf_perf_re` | 34776 | `0x079c2ece72373744` | `0x079c2ece738ea624` |
| 1 | 3476 | `a90_bpf_perf_re` | 34504 | `0x66fa9356f746c954` | `0x66fa9356f6f431d4` |
| 2 | 3476 | `a90_bpf_perf_re` | 34504 | `0x73079d4bfc1dd1a4` | `0x73079d4bfdaf2924` |
| 3 | 3476 | `a90_bpf_perf_re` | 34504 | `0x16a131be6b630e17` | `0x16a131be6ad1f697` |
| 4 | 3476 | `a90_bpf_perf_re` | 34504 | `0x5df58d570a79602a` | `0x5df58d570bcb98aa` |
| 5 | 3476 | `a90_bpf_perf_re` | 34504 | `0x059c35b354787914` | `0x059c35b355ca8194` |
| 6 | 3476 | `a90_bpf_perf_re` | 34504 | `0xc65df5f195a6a00d` | `0xc65df5f19414588d` |
| 7 | 3476 | `a90_bpf_perf_re` | 37706 | `0xac46dc06b9e72428` | `0xac46dc06b9d6c16c` |
| 8 | 3476 | `a90_bpf_perf_re` | 34916 | `0xba58f0f3fc0d659b` | `0xba58f0f3fdb4c4ef` |
| 9 | 3476 | `a90_bpf_perf_re` | 34916 | `0x2cc662848abefae5` | `0x2cc662848b075b91` |
| 10 | 3476 | `a90_bpf_perf_re` | 34504 | `0x04a139a959a18e1a` | `0x04a139a95813769a` |
| 11 | 3476 | `a90_bpf_perf_re` | 34916 | `0x6a06a044f846159a` | `0x6a06a044f9ffb4ee` |

## Interpretation

- P0 moves V2214 away from no-slide direct range lookup and into explicit slide scoring.
- P0 ranks a best candidate but does not promote it to exact because LR-callsite support is below threshold.
- P1 shows whether `_end_hyperdrive` labels are real generated-text hits or artifacts of missing slide correction.
- P2 keeps saved FP-chain LR decode conservative; ambiguous callsite-pair solutions are not promoted to exact unwind.

## Evidence

- V2214 summary: `workspace/private/runs/kernel/v2214-perf-regs-frame-sample-ring-5s-symbols-20260612-050706/summary.json`
- System.map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Kernel raw: `workspace/private/runs/kernel/v2197-stock-kallsyms/kernel.raw`
- Private result: `workspace/private/runs/kernel/v2215-perf-regs-ropp-jopp-classifier/result.json`

## Safety

- host_only: `true`
- live_device_access: `false`
- probe_write_user_executed: `false`
- cgroup_attach: `false`
- wifi_action: `false`
- flash_reboot: `false`
- partition_or_firmware_write: `false`
