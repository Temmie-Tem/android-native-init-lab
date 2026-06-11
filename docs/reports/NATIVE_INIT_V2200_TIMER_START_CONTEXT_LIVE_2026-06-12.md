# Native Init V2200 Timer Start Context Live Capture (2026-06-12)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)` stock kernel,
read-only BPF timer tracepoint path.

목적: V2199의 next unit인 same-boot `timer:timer_start` context capture를 수행해
dominant timer function pointer의 runtime cadence, current task, stackid를 확인한다.

범위: live read-only capture only. Helper deploy to `/cache/bin`, BPF
`timer:timer_start` attach, summary/stack map readback, post selftest. Flash/reboot,
Wi-Fi action, `probe_write_user`, cgroup attach, kernel/firmware/partition write 없음.

---

## 1. 결론

```text
decision: v2200-timer-start-context-captured-but-v2199-cadence-mismatch
run: workspace/private/runs/kernel/v2200-timer-start-context-20260612-003321
selftest: fail=0
```

V2200은 dominant timer pointer `0xffffff80083108fc`의 live context를 안정적으로
확보했다. 그러나 결과는 V2199의 `do_nocb_deferred_wakeup_timer` semantic lead를
**exact slide authority로 승격하지 못한다**.

핵심 판단:

- `timer_start.function=0xffffff80083108fc`는 이번 boot에서도 dominant였다.
- 8초 filtered capture에서 matching event `1396`개가 수집됐다.
- 모든 matching event의 `expires - now`가 `18000`이었다.
- `timeout_eq1=0`, `timeout_le4=0`, `timeout_eq18000=1396`.
- V2199의 RCU no-CB 근거였던 `mod_timer(&rdp->nocb_timer, jiffies + 1)` cadence와
  live cadence가 맞지 않는다.
- 따라서 `0x1bcebc` / `0x1bceb8`는 계속 **provisional**이다. WLAN/cfg80211 object
  chain에 exact symbol labels를 적용하면 안 된다.

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Helper source | `workspace/public/src/native-init/helpers/a90_bpf_timer_start_context.c` |
| Runner | `workspace/public/src/scripts/revalidation/native_kernel_timer_start_context_v2200.py` |
| Private run | `workspace/private/runs/kernel/v2200-timer-start-context-20260612-003321` |
| Context helper SHA256 | `f76a037b79b5e6cc64133bc56dc9db034a8d1d5ee16726b31daeb3b58f415654` |
| Trace extract helper SHA256 | `3f8510175ef0f7f7ac0564acd396f0fd82367e90a9095e1bcf61c2312b8f10ee` |
| Remote install path | `/cache/bin/a90_bpf_timer_start_context`, `/cache/bin/a90_bpf_trace_extract` |
| Post selftest | `pass=11 warn=1 fail=0` |

Command:

```sh
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_timer_start_context_v2200.py \
  --freq-duration 3 --context-duration 8 --top 16
```

---

## 3. Dominant Function Frequency

`a90_bpf_trace_extract` first re-measured the current boot; V2200 did not assume the
older V2196 boot pointer was still valid.

Top rows:

```text
0xffffff80083108fc count=694
0xffffff80081db824 count=66
0xffffff80081510c4 count=50
```

The same runtime pointer remains dominant in this boot, with a large margin over the
next timer function pointer.

---

## 4. Filtered Context Capture

Filtered command:

```text
/cache/bin/a90_bpf_timer_start_context \
  --filter-function 0xffffff80083108fc \
  --duration 8 \
  --allow-attach
```

Summary:

```text
count=1396
last_function=0xffffff80083108fc
last_timer=0xffffff800cbcbc58
last_expires=4306160631
last_now=4306142631
last_timeout=18000
last_flags=0x3
last_pid=3085
last_tgid=3085
last_stackid=76
comm=a90_bpf_timer_s
timeout_min=18000
timeout_max=18000
timeout_sum=25128000
timeout_eq1=0
timeout_le4=0
timeout_eq18000=1396
timeout_ge1000=1396
timeout_zero=0
```

Interpretation:

- The filtered pointer is not a sparse outlier; it fired about `174.5/s` during the
  8 second window.
- The timeout distribution is uniform: all `1396` events arm the timer exactly
  `18000` jiffies/ticks after `now`.
- `comm=a90_bpf_timer_s` is the current task at the tracepoint. It is not proof that
  the timer owner is the helper; it means this process context caused these
  `timer_start` events while the probe was attached.

---

## 5. Stack Map

The helper also captured stackid `76` and dumped the stack map value:

```text
0: 0xffffff80081dab48
1: 0xffffff80081dab48
2: 0xffffff80081dad68
3: 0xffffff800831067c
4: 0xffffff8008310584
5: 0xffffff8008158974
6: 0xffffff800810b7cc
7: 0xffffff8008103b00
```

All eight recovered IPs look like kernel virtual addresses. This preserves the V2195
capability result: stackmap raw IP recovery works despite `kptr_restrict` hiding
`/proc/kallsyms` addresses. It still does not provide exact names until the slide/JOPP/ROPP
ambiguity is solved.

---

## 6. V2199 Cross-Check

Under the V2199 leading slide hypotheses:

```text
0x1bcebc: 0xffffff80083108fc -> do_nocb_deferred_wakeup_timer+0x0
0x1bceb8: 0xffffff80083108fc -> do_nocb_deferred_wakeup_timer+0x4
```

The source xref for that callback is:

```c
setup_timer(&rdp->nocb_timer, do_nocb_deferred_wakeup_timer,
            (unsigned long)rdp);
mod_timer(&rdp->nocb_timer, jiffies + 1);
```

V2200 live data does not match that arm cadence. The capture saw:

```text
timeout_eq1=0
timeout_eq18000=1396
```

Therefore V2200 refines V2199 as follows:

- Function-name mapping to the RCU no-CB callback remains a plausible semantic lead.
- The cadence evidence that made it attractive is contradicted by live data.
- `exact_symbolization=false` must remain in force.
- Any downstream symbol labels derived from `0x1bcebc` must be marked provisional.

---

## 7. Safety

Verified safety properties for this unit:

- No flash or reboot.
- No Wi-Fi scan/connect/credential/DHCP/route/ping action.
- No `probe_write_user` execution.
- No cgroup BPF attach.
- BPF program type: tracepoint observation only.
- BPF attach target: `timer:timer_start` only.
- Post-run selftest: `fail=0`.

The only intentional filesystem change on the device was helper deployment under
`/cache/bin`, matching the existing rollbackable live-validation pattern.

---

## 8. Next

Recommended next unit:

1. Update the V2199 scorer to ingest V2200 live timeout distribution and penalize
   candidates whose source cadence conflicts with `timeout=18000`.
2. Add a V2201 read-only timer-object probe for the same function pointer: read the
   `struct timer_list` object behind `ctx->timer` using source-derived offsets
   (`expires`, `function`, `data`, flags/base-related fields). The `data` pointer is the
   likely discriminator between RCU no-CB, key GC, and another timer owner.
3. Keep stack symbolization provisional until a slide is selected by independent,
   non-conflicting evidence.
