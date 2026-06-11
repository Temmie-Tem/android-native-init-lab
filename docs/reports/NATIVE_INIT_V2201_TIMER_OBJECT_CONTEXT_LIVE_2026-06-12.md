# Native Init V2201 Timer Object Context Live Capture (2026-06-12)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)` stock kernel,
read-only BPF `timer:timer_start` object read-chain path.

목적: V2200에서 남은 ambiguity를 줄이기 위해, dominant `timer_start.function`
포인터만 보지 않고 tracepoint record의 `timer` 포인터에서 실제 `struct timer_list`
필드를 읽는다.

범위: live read-only capture only. Helper deploy to `/cache/bin`, BPF tracepoint attach,
summary/stack map readback, post selftest. Flash/reboot, Wi-Fi action, `probe_write_user`,
cgroup attach, kernel/firmware/partition write 없음.

---

## 1. 결론

```text
decision: v2201-timer-object-read-chain-pass-rcu-lead-refuted-observer-context-unresolved
run: workspace/private/runs/kernel/v2201-timer-object-context-20260612-004934
selftest: fail=0
```

V2201은 `timer:timer_start` record의 `timer` 포인터에서 `struct timer_list` 객체를
읽는 체인을 live로 확인했다. 객체 읽기 자체는 안정적이다.

핵심 결과:

- dominant function pointer는 다시 `0xffffff80083108fc`였다.
- filtered object capture는 8초 동안 `1396` hit를 수집했다.
- `obj_read_errors=0`.
- `obj_function_match=1396/1396`.
- `obj_expires_match=1396/1396`.
- `expires - now = 18000`이 전 hit에서 유지됐다.
- 객체 데이터는 `obj_data = timer - 0x10`이었다.
- 이 객체 불변식은 V2199의 RCU no-CB lead와 V2198의 broad timer callback leads를
  exact symbol authority로 쓰기 어렵게 만든다.

따라서 V2201의 판정은 다음과 같다.

```text
object_read_chain: live-pass
v2199_rcu_nocb_lead: refuted-as-exact-authority
v2198_key_gc/static-callback_leads: refuted-as-exact-authority
exact_symbolization: still-forbidden
next_required: non-owner comm/object-discriminator or multi-object histogram
```

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Object helper | `workspace/public/src/native-init/helpers/a90_bpf_timer_object_context.c` |
| Trace helper update | `workspace/public/src/native-init/helpers/a90_bpf_trace_extract.c` |
| Runner | `workspace/public/src/scripts/revalidation/native_kernel_timer_object_context_v2201.py` |
| Private run | `workspace/private/runs/kernel/v2201-timer-object-context-20260612-004934` |
| Live object helper SHA256 | `6621352fc48a1d7db8943f26d396fd725a2c6dd1fe81cb04f8da6857b573e8c8` |
| Current object helper SHA256 | `2d3ca0d7a3fc8c396b9351bde31ad7c5851cac8feb2e193482dd3937dc295697` |
| Trace helper SHA256 | `471eaef5f4b59e58cc73a28f5ead1d2cc0e29fe05e7b1b3965a23ea3b3ec7484` |
| Remote install path | `/cache/bin/a90_bpf_timer_object_context`, `/cache/bin/a90_bpf_trace_extract` |
| Post selftest | `fail=0` |

Command:

```sh
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_timer_object_context_v2201.py \
  --freq-duration 3 --context-duration 8 --top 16
```

Both the frequency phase and object-context phase used `--busy-observe`, so the helper
no longer sleeps during the observation window. After the live run, the object helper
result string was corrected from `timer-start-context` to `timer-object-context`; the
current-source SHA above reflects that cosmetic rebuild.

---

## 3. Frequency Phase

The run re-measured the current boot before filtering the object capture.

Top rows:

```text
0xffffff80083108fc count=695
0xffffff80081db824 count=180
0xffffff80081510c4 count=50
0xffffff8008a1e884 count=4
```

This confirms the same dominant function pointer as V2200. The absolute rate changed only
slightly, and the top pointer remained separated from the next candidate.

---

## 4. Object Capture

Filtered command:

```sh
/cache/bin/a90_bpf_timer_object_context \
  --filter-function 0xffffff80083108fc \
  --duration 8 \
  --busy-observe \
  --allow-attach
```

Summary line:

```text
summary count=1396 last_function=0xffffff80083108fc last_timer=0xffffff8012513c58 \
last_expires=4306257942 last_now=4306239942 last_timeout=18000 last_flags=0x7 \
last_pid=3131 last_tgid=3131 last_stackid=76 comm=a90_bpf_timer_o \
timeout_min=18000 timeout_max=18000 timeout_sum=25128000 timeout_eq1=0 \
timeout_le4=0 timeout_eq18000=1396 timeout_ge1000=1396 timeout_zero=0 \
obj_entry_next=0xffffffc173dd4000 obj_entry_pprev=0x0000000000000000 \
obj_expires=4306257942 obj_function=0xffffff80083108fc \
obj_data=0xffffff8012513c48 obj_flags=0x7 obj_read_errors=0 \
obj_function_match=1396 obj_expires_match=1396
```

Derived object facts:

```text
timer                  = 0xffffff8012513c58
obj_data               = 0xffffff8012513c48
obj_data - timer       = -0x10
obj_function == record = true for 1396/1396
obj_expires == record  = true for 1396/1396
expires - now          = 18000 for 1396/1396
obj_flags              = 0x7
```

This is the first live confirmation that the record pointer can be used as a stable object
anchor for `struct timer_list` field extraction.

---

## 5. Candidate Impact

### V2199 RCU no-CB Lead

V2199's strongest candidate mapped `0xffffff80083108fc` to
`do_nocb_deferred_wakeup_timer` under slide `0x1bcebc`. V2200 already contradicted its
`jiffies + 1` cadence with `timeout=18000`. V2201 adds a second, stronger discriminator:

- RCU no-CB uses `setup_timer(&rdp->nocb_timer, do_nocb_deferred_wakeup_timer,
  (unsigned long)rdp)`.
- A `struct rcu_data` object is not expected to sit exactly at `timer - 0x10`.
- V2201 observed `obj_data = timer - 0x10`.

This refutes the RCU no-CB mapping as an exact slide authority for this pointer.

### V2198 Broad Timer Leads

V2198/V2199 also included broad semantic candidates such as `key_gc_timer_func`,
`poll_spurious_irqs`, and `pstore_timefunc`. The static `DEFINE_TIMER(..., data=0)` style
leads are also inconsistent with V2201 because `obj_data` is a non-zero pointer at
`timer - 0x10`.

### Current `comm` Caveat

The captured `comm` is `a90_bpf_timer_o`, but this is not an owner proof. `timer_start`
runs in the context that arms the timer, or in the interrupted current task for some paths.
It is useful as an observer-context warning, not as a symbol owner label. Do not identify
`0xffffff80083108fc` by `comm` alone.

---

## 6. What Changed Since V2200

| Question | V2200 | V2201 |
| --- | --- | --- |
| Dominant pointer still present? | yes | yes |
| Cadence | `timeout=18000` | `timeout=18000` |
| Object read-chain | not captured | **live-pass** |
| `timer->function` check | not captured | **1396/1396 match** |
| `timer->expires` check | not captured | **1396/1396 match** |
| `timer->data` discriminator | absent | **`timer - 0x10`** |
| RCU no-CB exact lead | weakened by cadence | **refuted as exact authority** |
| Exact symbolization | false | false |

V2201 closes the object-read part of the timer discriminator. It does not close exact
symbolization; instead, it removes the leading false authority.

---

## 7. Next

Recommended next unit:

1. Build a read-only top-row timer object discriminator that records multiple function
   pointers with `(function, timeout, obj_data_delta, flags, stackid, comm)` rather than
   filtering only one pointer.
2. Treat `comm` as context, not ownership. Prefer object invariants and source-backed
   timer setup patterns.
3. Keep exact symbol labels disabled until at least one candidate satisfies both object
   invariants and an independent stack/callsite constraint.
4. Do not execute `probe_write_user`, cgroup attach, or any mutating BPF path.

---

## 8. V2202 Follow-Up

V2202 extended the single-filter object capture into a multi-row timer object histogram.
It confirmed that the V2201 top row `0xffffff80083108fc` remains stable with
`timeout=18000` and `obj_data_delta=-16`, but it also separated the RCU-like behavior into
a different raw function row: `0xffffff80081db824` with `comm=rcu_preempt` and
`timeout_min=1`.

This strengthens the V2201 conclusion: the top row is not the RCU no-CB exact authority.
The next step is row-to-source pattern matching, not naming the dominant raw pointer.
