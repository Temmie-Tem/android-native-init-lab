# Native Init V2197 Stock Kallsyms Symbolization (2026-06-11)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)` stock kernel blob.

목적: V2196에서 막힌 P1b exact gate, 즉 live stock kernel과 일치하는 symbol map을
host-only로 복구하고 V2195 stackmap raw IP를 다시 symbolization 한다.

범위: host-only parser 구현·실행 + 기존 V2195/V2196 evidence 재분석. 새 live device
명령, flash, reboot, Wi-Fi scan/connect, credential, DHCP/routes, external ping,
`probe_write_user`, cgroup attach 없음.

---

## 1. 결론

P1b의 artifact gap은 닫혔다.

```text
decision: stock-kallsyms-extract-pass
decision: kernel-stack-symbolization-pass
exact_symbolization: true
```

V2196에서 생성한 OSRC rebuild `System.map`은 live kernel과 SHA가 달라 authority가
아니었다. V2197은 같은 live stock wrapper blob에서 embedded kallsyms를 직접 파싱해
stock `System.map`을 생성했다.

중요한 보정:

- stackmap raw IP는 stock map + sched_switch 문맥의 `__schedule` slide로 symbolization 가능하다.
- timer function anchors는 raw callback pointer bank로는 유효하지만, 현재 scoring에서는 여러
  slide가 timer pointers를 임의 text symbol 중간이나 entry에 그럴듯하게 맞출 수 있다.
- 따라서 timer anchors는 이번 run에서 slide authority로 승격하지 않는다. timer callback 이름은
  별도 callback-entry/tracepoint 검증 전까지 보조 evidence다.

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Extractor | `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py` |
| Stock map | `workspace/private/runs/kernel/v2197-stock-kallsyms/System.map` |
| Extract JSON | `workspace/private/runs/kernel/v2197-stock-kallsyms/stock-kallsyms.json` |
| Symbolization JSON | `workspace/private/runs/kernel/v2197-stock-kallsyms/symbolization.json` |
| Symbolization summary | `workspace/private/runs/kernel/v2197-stock-kallsyms/symbolization.md` |

검증:

```sh
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py \
  workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py
```

---

## 3. Stock Kallsyms Parse

입력 kernel wrapper:

```text
workspace/private/runs/kernel/v2196-boot-kernel-compare/unpack/kernel
```

SHA:

```text
wrapper_sha256: 9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a
raw_sha256:     06d3db982afe911c50d18eccfdda809d109b8330b2a55403b19fe82b78bfdb71
raw_offset:     20
raw_size:       48830480
```

Recovered kallsyms layout:

```text
token_table_start: 0x2103100
token_table_end:   0x21034ab
token_index_start: 0x2103500
marker_start:      0x2101f00
marker_count:      576
names_start:       0x1f10700
names_end:         0x2101e55
num_syms_pos:      0x1f10600
num_syms:          147295
offsets_start:     0x1e8087c
relative_base_pos: 0x1f105f8
relative_base_raw: 0x0
```

The parser validates the layout with:

- token table cumulative offsets matching `kallsyms_token_index` after padding.
- marker offsets matching every 256th decoded name record.
- required known symbols present: `T_text`, `T_stext`,
  `ttrace_event_raw_event_sched_switch`, `tperf_trace_sched_switch`,
  `Ttrace_call_bpf`, `Tbpf_get_stackid`, `t__schedule`, `tmdm_subsys_powerup`.
- monotonic `kallsyms_offsets` table.

Synthetic address base:

```text
synthetic_text_address: 0xffffff8008080000
text_offset:            0x4ef4
synthetic_base:         0xffffff800807b10c
```

The raw address table stores low offsets with `relative_base_raw=0`. The emitted
`System.map` anchors `_text` at `0xffffff8008080000` and lets runtime KASLR slide
be solved from live stack IPs.

Representative stock symbols:

```text
ffffff80080e4e68 t trace_event_raw_event_sched_switch
ffffff80080e4fe8 t perf_trace_sched_switch
ffffff80081c2848 T trace_call_bpf
ffffff80081e9680 T bpf_get_stackid
ffffff80099c3258 t __schedule
ffffff800956e298 t mdm_subsys_powerup
```

---

## 4. Stack Symbolization

Command:

```sh
python3 workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py \
  --system-map workspace/private/runs/kernel/v2197-stock-kallsyms/System.map \
  --live-kernel workspace/private/runs/kernel/v2196-boot-kernel-compare/unpack/kernel \
  --candidate-image workspace/private/runs/kernel/v2196-boot-kernel-compare/unpack/kernel \
  --stack-log workspace/private/runs/kernel/v2195-stackmap-dump-20260611-203700/rerun/logs/host/helper-stackdump.stdout.txt \
  --timer-log workspace/private/runs/kernel/v2196-p1b-symbolization/logs/host/timer-function-freq.stdout.txt \
  --out-json workspace/private/runs/kernel/v2197-stock-kallsyms/symbolization.json \
  --out-md workspace/private/runs/kernel/v2197-stock-kallsyms/symbolization.md
```

Result:

```text
decision: kernel-stack-symbolization-pass
exact_symbolization: true
reason: candidate kernel hash matches live boot kernel and all stack IPs map under one stack-context slide
hash_match: true
best_slide: 0x7f0dc
source: __schedule from 0xffffff8009a42334
stack_score: 6/6
timer_weighted_score: 415/415
timer_entry_weighted_score: 0/415
timer_near_entry_weighted_score: 35/415
full_stack_candidate_count: 4
timer_functions_are_slide_authority: false
```

Best sched_switch-context stack mapping:

```text
0xffffff8009a42334 -> __schedule+0x0
0xffffff8009a42334 -> __schedule+0x0
0xffffff8009a429d8 -> bit_wait_io+0x4
0xffffff800819ad8c -> do_wait_intr_irq+0x0
0xffffff800819adf0 -> do_wait_intr_irq+0x64
0xffffff80081131f4 -> perf_trace_ipi_handler+0x10
```

Interpretation:

- `stackid -> raw IP -> symbol+offset` path is now end-to-end operational.
- The chosen slide is anchored by the sched_switch stack's `__schedule` frame.
- Other mathematical slide candidates still exist because four candidate slides map
  all stack IPs, and many arbitrary slides map all timer pointers somewhere inside
  text.
- The best sched_switch-context slide has `timer_entry_weighted_score=0/415`, so
  timer callback names are not treated as independent slide proof in this report.

---

## 5. Capability Map Delta

| Capability | V2196 | V2197 |
| --- | --- | --- |
| raw stack IP recovery | pass | pass |
| raw timer function pointer recovery | pass | pass |
| matching stock symbol map | blocked | **pass** |
| stack raw IP symbolization | blocked | **pass** |
| timer callback semantic naming | weak/blocked | still weak; needs callback-entry validation |
| kernel write / `probe_write_user` | forbidden | forbidden |

V2197 closes the stock map artifact gap. It does not change the write boundary.

---

## 6. Next

Recommended next unit:

1. Apply the stock map to WLAN/cfg80211/QRTR tracepoints with the updated symbolizer
   ambiguity metrics enabled.
2. Treat timer callback naming as a separate validation problem; do not use it as
   slide authority until callback-entry evidence is added.
3. For WLAN object-chain work, keep writes blocked and use source offset + structure
   invariants as planned in V2194.
