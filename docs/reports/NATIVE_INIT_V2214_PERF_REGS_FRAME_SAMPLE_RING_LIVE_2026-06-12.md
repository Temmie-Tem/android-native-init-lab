# Native Init V2214 Perf Regs Frame Sample Ring

## Decision

- Decision: `v2214-perf-regs-frame-sample-ring-captured`
- Pass: `true`
- Total samples observed: `80`
- Printed samples parsed: `80`
- Occupied ring slots: `80` / `1024`
- Selftest fail=0: `true`

## Method

- Uses bounded BPF array maps: one stats row plus a 1024-slot sample ring.
- Supports per-CPU software CPU-clock perf events; no unbounded kernel storage is used.
- Samples live perf-event `pt_regs` x29/LR/SP/PC plus raw FP slots with `bpf_probe_read` only.
- Does not use `probe_write_user`, cgroup attach, Wi-Fi, flash, reboot, or partition/firmware writes.

## Metrics

- Unique comms: `6`
- Unique pids: `6`
- Walkable `fp_slot_next`: `80`
- Walkable `fp2_slot_next`: `78`
- Raw LR nonzero: `80`
- Raw LR in kernel text: `0`
- Raw LR kernel VA outside text: `0`
- Live ctx PC in kernel text: `80`
- Live ctx LR nonzero: `80`
- Live ctx LR in kernel text: `80`
- Live ctx LR kernel VA outside text: `0`
- Direct stock-map ctx PC hits: `80` / `80`
- Direct stock-map ctx LR hits: `80` / `80`

| Field | Unique Count | Preview |
| --- | ---: | --- |
| `ctx_pc` | 43 | 0xffffff80081d87dc, 0xffffff80081e18b0, 0xffffff80081e7cb4, 0xffffff8008219b4c, 0xffffff8008219ba4, 0xffffff8008219de8, 0xffffff80082eb9e0, 0xffffff800831b330, 0xffffff800831d160, 0xffffff8008321c8c, 0xffffff800832f320, 0xffffff800832f350 |
| `fp_slot_raw_lr` | 78 | 0x029a30b0517bc0b6, 0x04a139a959a18e1a, 0x059c35b354787914, 0x079c2ece72373744, 0x079c38aa5978d9b6, 0x0ca33ba9a3d275b7, 0x0fa83e851d4662ec, 0x12c56ec679f31eec, 0x13cc7d59d09e5e5c, 0x14b14af4a5d968e5, 0x16a131be6b630e17, 0x19ca5ccdab329500 |
| `fp_slot_next` | 33 | 0xffffff800bc33cc0, 0xffffff800bc33d90, 0xffffff8013b5bad0, 0xffffff8013b5bb00, 0xffffff8013be3940, 0xffffff8013be3ac0, 0xffffff8013cf3c60, 0xffffff8013cf3d00, 0xffffff8013cf3d80, 0xffffff8013cf3e30, 0xffffff8013cf3e50, 0xffffff8013cf3e90 |
| `fp2_slot_raw_lr` | 76 | 0x029a30b051758062, 0x04a139a95813769a, 0x059c35b355ca8194, 0x079c2ece738ea624, 0x079c38aa59769962, 0x0ca33ba9a3dc3563, 0x0fa83e851d268044, 0x12c56ec67993fc70, 0x13cc7d59d09d15e0, 0x14b14af4a460c991, 0x16a131be6ad1f697, 0x19ca5ccdab315694 |
| `ctx_lr` | 40 | 0xffffff8008107a5c, 0xffffff8008107bac, 0xffffff800816ddcc, 0xffffff800819a40c, 0xffffff80081d87f8, 0xffffff80081db38c, 0xffffff80081dd12c, 0xffffff80081dd424, 0xffffff80081ddbb0, 0xffffff80081e7c7c, 0xffffff8008219b98, 0xffffff8008219ee8 |

## Staged Comparison

| Window | Samples | Occupied Ring | Unique `ctx_pc` | Unique `ctx_lr` | Raw FP LR in Text | Selftest |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 250ms fixed-key run | 2 | 2 / 1024 | 2 | 2 | 0 | fail=0 |
| 5s final run | 80 | 80 / 1024 | 43 | 40 | 0 | fail=0 |

- The old V2213 saved-thread anchor stayed flat because `thread.cpu_context.pc` is a scheduler resume point.
- V2214 uses the live perf-event register context; both `ctx_pc` and live `ctx_lr` diversify with runtime.
- Saved FP-chain LR fields remain ROPP-encoded, so the next step is ROPP/JOPP-aware decode rather than longer sampling.

## Direct Symbol Preview

- Stock map: `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map`
- Text symbols loaded: `77770`

| Source | Count | Address | Symbol | Offset |
| --- | ---: | --- | --- | ---: |
| `ctx_pc` | 21 | `0xffffff8009a4825c` | `_end_hyperdrive` | `283136` |
| `ctx_pc` | 17 | `0xffffff8009a482b4` | `_end_hyperdrive` | `283224` |
| `ctx_pc` | 2 | `0xffffff800854a1c0` | `blkg_lookup_create` | `112` |
| `ctx_pc` | 1 | `0xffffff8009a429a0` | `_end_hyperdrive` | `260420` |
| `ctx_pc` | 1 | `0xffffff80082eb9e0` | `sys_epoll_create1` | `256` |
| `ctx_pc` | 1 | `0xffffff80083b9160` | `trace_raw_output_jbd2_handle_start` | `2576` |
| `ctx_pc` | 1 | `0xffffff8009a4f594` | `_end_hyperdrive` | `312632` |
| `ctx_pc` | 1 | `0xffffff800831d160` | `dqget` | `248` |
| `ctx_pc` | 1 | `0xffffff80083394d8` | `__kernfs_new_node` | `360` |
| `ctx_pc` | 1 | `0xffffff80085dad2c` | `pmic_mpp_get_group_name` | `60` |
| `ctx_pc` | 1 | `0xffffff8008520134` | `elv_completed_request` | `76` |
| `ctx_pc` | 1 | `0xffffff800851b884` | `bvec_free` | `260` |
| `ctx_lr` | 17 | `0xffffff800816ddcc` | `tick_setup_periodic` | `6644` |
| `ctx_lr` | 12 | `0xffffff80081dd424` | `bpf_get_file_flag` | `300` |
| `ctx_lr` | 3 | `0xffffff8008a34a18` | `scsi_seq_show` | `144` |
| `ctx_lr` | 3 | `0xffffff8008549728` | `bounce_end_io_read_isa` | `384` |
| `ctx_lr` | 3 | `0xffffff80081ddbb0` | `__bpf_prog_charge` | `176` |
| `ctx_lr` | 2 | `0xffffff80085151f0` | `ecc_point_mult` | `112` |
| `ctx_lr` | 2 | `0xffffff800851b814` | `bvec_free` | `148` |
| `ctx_lr` | 2 | `0xffffff80081e7c7c` | `bpf_lru_populate` | `340` |
| `ctx_lr` | 2 | `0xffffff8008219b98` | `__put_page` | `528` |
| `ctx_lr` | 2 | `0xffffff80081d87f8` | `bpf_jit_compile` | `792` |
| `ctx_lr` | 2 | `0xffffff800832f31c` | `proc_pid_status` | `948` |
| `ctx_lr` | 2 | `0xffffff80086c1d0c` | `query_usecase` | `372` |

## Interpretation

- V2214 confirms the useful ROPP-bypass anchor is live perf-event `ctx_pc` plus live `ctx_lr`.
- The saved FP-chain LR slots remain mostly ROPP-encoded and are not a completed unwind path.
- Direct stock-map symbol previews are range lookups for orientation, not final exact call-graph proof.
- `_end_hyperdrive` hits should be treated as unresolved generated/late-text territory until ROPP/JOPP-aware decoding is applied.

## Source Basis

- `bpf_perf_event_data` exposes `struct pt_regs regs` in the UAPI header.
- `pe_prog_convert_ctx_access` rewrites default perf-event ctx reads through `bpf_perf_event_data_kern->regs`.
- arm64 `pt_regs` layout is `regs[31], sp, pc, pstate`; generated offsets confirm LR=240, SP=248, PC=256.

## Convergence

- Ring saturated: `false`
- Hint: ring not saturated; longer duration can still add information

## Safety

- cgroup_attach: `false`
- flash_reboot: `false`
- partition_or_firmware_write: `false`
- probe_write_user_executed: `false`
- read_only_bpf: `true`
- wifi_action: `false`

## Evidence

- Private run: `workspace/private/runs/kernel/v2214-perf-regs-frame-sample-ring-5s-symbols-20260612-050706`
- Helper SHA-256: `40d178caa49129b9b42415371b3bc84f7172df9b6e6d038d779b5a26f125ffcf`
